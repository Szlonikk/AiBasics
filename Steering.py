
import random
import math
import pygame
from typing import List, Tuple
from Collider import Collider
from Settings import (
    WIDTH, HEIGHT,
    ZOMBIE_WANDER_CIRCLE_DISTANCE,
    ZOMBIE_WANDER_CIRCLE_RADIUS,
    ZOMBIE_WANDER_JITTER,
    ZOMBIE_SEPARATION_RADIUS,
)

Vec2 = pygame.math.Vector2

def truncate(v: Vec2, max_value: float) -> Vec2:
    if v.length_squared() > max_value * max_value:
        return v.normalize() * max_value
    return v

def seek(position: Vec2, target: Vec2, max_speed: float) -> Vec2:
    desired = (target - position).normalize() * max_speed if target != position else Vec2()
    return desired

def flee(position: Vec2, target: Vec2, max_speed: float) -> Vec2:
    desired = (position - target)
    if desired.length_squared() > 0:
        desired = desired.normalize() * max_speed
    return desired

def separation(me: Collider, others: List[Collider]) -> Vec2:
    force = Vec2()
    for o in others:
        if o is me: 
            continue
        to_me = me.pos - o.pos
        dist = to_me.length()
        if 0 < dist < ZOMBIE_SEPARATION_RADIUS + me.radius + o.radius:
            force += to_me.normalize() / max(dist, 0.0001)
    return force

def wander(heading: Vec2, wander_target: Vec2) -> Tuple[Vec2, Vec2]:
    # Buckland-style wander target jitter on a circle projected ahead
    jitter = ZOMBIE_WANDER_JITTER
    wander_target += Vec2(random.uniform(-1, 1) * jitter, random.uniform(-1, 1) * jitter)
    if wander_target.length_squared() > 0:
        wander_target = wander_target.normalize() * ZOMBIE_WANDER_CIRCLE_RADIUS
    circle_center = heading.normalize() * ZOMBIE_WANDER_CIRCLE_DISTANCE
    target_world = circle_center + wander_target
    return target_world, wander_target

def obstacle_avoidance(me: Collider, velocity: Vec2, obstacles: List[Collider], look_ahead: float = 80.0) -> Vec2:
    # simple feeler: check along velocity
    if velocity.length_squared() == 0:
        return Vec2()
    feeler = velocity.normalize() * look_ahead
    closest_dist = math.inf
    closest = None
    closest_normal = Vec2()

    for o in obstacles:
        # project center onto feeler line
        to_o = o.pos - me.pos
        t = max(0.0, min(1.0, to_o.dot(feeler) / (feeler.length_squared())))
        closest_point = me.pos + feeler * t
        # if circle intersects with feeler swept circle
        if closest_point.distance_to(o.pos) < o.radius + me.radius + 6:
            d = me.pos.distance_to(o.pos)
            if d < closest_dist:
                closest_dist = d
                closest = o
                # normal away from obstacle center
                closest_normal = (me.pos - o.pos).normalize() if me.pos != o.pos else Vec2(1,0)

    if closest:
        # steer away proportional to proximity
        return closest_normal * (look_ahead / max(closest_dist, 1.0))
    return Vec2()

def wall_avoidance(me: Collider, velocity: Vec2) -> Vec2:
    # Predict next position and push back from walls (acts like "bounce" intent)
    nudge = Vec2()
    future = me.pos + velocity * 0.4
    if future.x - me.radius < 0: nudge.x += 1
    if future.x + me.radius > WIDTH: nudge.x -= 1
    if future.y - me.radius < 0: nudge.y += 1
    if future.y + me.radius > HEIGHT: nudge.y -= 1
    return nudge * velocity.length()

def line_intersects_circle(a: Vec2, b: Vec2, circle_center: Vec2, circle_radius: float) -> bool:
    ab = b - a
    ac = circle_center - a
    t = 0.0
    denom = ab.length_squared()
    if denom > 0:
        t = max(0.0, min(1.0, ac.dot(ab) / denom))
    closest = a + ab * t
    return closest.distance_to(circle_center) <= circle_radius

def ray_circle_hit_point(ray_start, ray_end, circle_center, radius):
    # Ray parametric form: P = A + t*(B-A)
    # Solve intersection with circle
    d = ray_end - ray_start
    f = ray_start - circle_center

    a = d.dot(d)
    b = 2 * f.dot(d)
    c = f.dot(f) - radius*radius

    disc = b*b - 4*a*c
    if disc < 0:
        return None  # no hit

    disc = disc**0.5
    t1 = (-b - disc) / (2*a)
    t2 = (-b + disc) / (2*a)

    # We want the first hit along the ray in [0,1]
    ts = []
    if 0 <= t1 <= 1:
        ts.append(t1)
    if 0 <= t2 <= 1:
        ts.append(t2)

    if not ts:
        return None

    t = min(ts)
    return ray_start + d * t
