
import random
import math
import pygame
from typing import List, Tuple
from enum import Enum
from Collider import Collider
from Settings import (
    WIDTH, HEIGHT,
    ZOMBIE_WANDER_CIRCLE_DISTANCE,
    ZOMBIE_WANDER_CIRCLE_RADIUS,
    ZOMBIE_WANDER_JITTER,
    ZOMBIE_SEPARATION_RADIUS,
    ZOMBIE_PANIC_DISTANCE,
    ZOMBIE_DECELERATION_TWEAKER,
    ZOMBIE_FACING_ANGLE,
    ZOMBIE_RADIUS,
    ZOMBIE_BREAKING_WEIGHT,
    ZOMBIE_DISTANCE_FROM_BOUNDARY,
)

Vec2 = pygame.math.Vector2

class Deceleration(Enum):
    slow = 1
    normal = 2
    fast = 3

def truncate(v: Vec2, max_value: float) -> Vec2:
    if v.length_squared() > max_value * max_value:
        return v.normalize() * max_value
    return v

def seek(position: Vec2, target: Vec2, max_speed: float, velocity: float) -> Vec2:
    desired = (target - position).normalize() * max_speed
    return desired - velocity

def flee(position: Vec2, target: Vec2, max_speed: float, velocity: float) -> Vec2:
    panicDistanceSq = ZOMBIE_PANIC_DISTANCE * ZOMBIE_PANIC_DISTANCE
    desired = position - target
    if desired.length_squared() > panicDistanceSq:
        return Vec2(0, 0)
    desired = desired.normalize() * max_speed
    return desired - velocity

def arrive(position: Vec2, target: Vec2, max_speed: float, velocity: float, deceleration: Deceleration):
    toTarget = target - position
    dist = target.length()
    if dist > 0.0:
        decelerationTweaker = ZOMBIE_DECELERATION_TWEAKER
        speed = min(dist / (deceleration.value * decelerationTweaker), max_speed)
        desired = toTarget * speed / dist
        return desired - velocity
    return Vec2(0, 0)

def pursuit(position: Vec2, heading: Vec2, evader: Vec2, evaderHeading: Vec2, evaderVelocity: Vec2, evaderSpeed: float, max_speed: float, velocity: float):
    toEvader = evader - position
    relativeHeading = heading.dot(evaderHeading)
    if toEvader.dot(heading) > 0 and relativeHeading > -math.cos(ZOMBIE_FACING_ANGLE):
        return seek(position, evader, max_speed, velocity)
    
    lookAheadTime = toEvader.length() / (max_speed + evaderSpeed)
    return seek(position, evader + evaderVelocity * lookAheadTime, max_speed, velocity)
    
def evade(pursuer_pos: Vec2, pursuer_vel: Vec2, position: Vec2, max_speed: float, velocity: Vec2) -> Vec2:
    to_pursuer = pursuer_pos - position
    pursuer_speed = pursuer_vel.length()
    look_ahead_time = to_pursuer.length() / (max_speed + pursuer_speed)
    return flee(position, pursuer_pos + pursuer_vel * look_ahead_time, max_speed, velocity) 

def separation(me, neighbours: List) -> Vec2:
    force = Vec2()
    for n in neighbours:
        if n is not me and n.tagged: 
            to_me = me.collider.pos - n.collider.pos
            force += to_me.normalize() / to_me.length()
    return force

def alignment(me, neighbours: List) -> Vec2:
    average_heading = Vec2()
    neighbour_count = 0.0
    for n in neighbours:
        if n is not me and n.tagged:
            average_heading += n.vel.normalize()
            neighbour_count += 1.0
    if neighbour_count > 0.0:
        average_heading /= neighbour_count
        average_heading -= me.vel.normalize()
    return average_heading

def cohesion(me, max_speed: float, neighbours: List) -> Vec2:
    center_of_mass = Vec2()
    force = Vec2()
    neighbour_count = 0.0
    for n in neighbours:
        if n is not me and n.tagged:
            center_of_mass  += n.collider.pos
            neighbour_count += 1
    if neighbour_count > 0.0:
        center_of_mass /= neighbour_count
        force = seek(me.collider.pos, center_of_mass, max_speed, me.vel)
    return force

def wander(heading: Vec2, wander_target: Vec2) -> Tuple[Vec2, Vec2]: #TODO
    # Buckland-style wander target jitter on a circle projected ahead
    jitter = ZOMBIE_WANDER_JITTER
    wander_target += Vec2(random.uniform(-1, 1) * jitter, random.uniform(-1, 1) * jitter)
    wander_target = wander_target.normalize() * ZOMBIE_WANDER_CIRCLE_RADIUS
    circle_center = heading.normalize() * ZOMBIE_WANDER_CIRCLE_DISTANCE
    target_world = circle_center + wander_target
    return target_world, wander_target

def obstacle_avoidance(me: Collider, velocity: Vec2, speed: float, max_speed: float, obstacles: List[Collider], look_ahead: float = 80.0) -> Vec2:
    boxLength = look_ahead + (speed / max_speed) * look_ahead
    closest_dist = math.inf
    closest = None

    # tag all obstacles
    for ob in obstacles:
            ob.tagged = False   # clear any previous tag

            # distance from vehicle to obstacle
            dist_sq = (ob.pos - me.pos).length_squared()

            if dist_sq < ZOMBIE_RADIUS * ZOMBIE_RADIUS:
                ob.tagged = True


    heading = Vec2(0, 0)
    if velocity.length() > 0.0:
        heading = velocity.normalize()
    side = (heading.y * -1, heading.x)

    for o in obstacles:
        if o.tagged:
            localPos = point_to_local_space(o.pos, heading, side, me.pos)
            if localPos >= 0:
                expandedRadius = o.radius + ZOMBIE_RADIUS
                if abs(localPos.y) < expandedRadius:
                    cX = localPos.x
                    cY = localPos.y
                    sqrtPart = math.sqrt(expandedRadius * expandedRadius - cY * cY)
                    ip = cX - sqrtPart
                    if ip <= 0:
                        ip = cX + sqrtPart
                    if ip < closest_dist:
                        closest_dist = ip
                        closest = o
    if closest:
        steeringForce = Vec2()
        multiplier = 1.0 + (boxLength - closest.pos.x) / boxLength
        steeringForce.y = (closest.radius - closest.pos.y) * multiplier
        steeringForce.x = (closest.radius - closest.pos.x) * ZOMBIE_BREAKING_WEIGHT
        # steer away proportional to proximity
        return vector_to_world_space(steeringForce, heading, side)
    return Vec2(0, 0)

def wall_avoidance(me: Collider, velocity: Vec2) -> Vec2:
    # Predict next position and push back from walls (acts like "bounce" intent)
    nudge = Vec2()
    future = me.pos + velocity * 0.4
    if future.x - me.radius < 0: nudge.x += 1
    if future.x + me.radius > WIDTH: nudge.x -= 1
    if future.y - me.radius < 0: nudge.y += 1
    if future.y + me.radius > HEIGHT: nudge.y -= 1
    return nudge * velocity.length()


def get_hiding_position(pos_ob: Vec2, radius_ob: float, target_pos: Vec2) -> Vec2:
    dist_away = radius_ob + ZOMBIE_DISTANCE_FROM_BOUNDARY
    to_ob = (pos_ob - target_pos).normalize()
    return (to_ob * dist_away) + pos_ob

def hide(position: Vec2, max_speed: float, velocity: Vec2, target_pos: Vec2, target_vel: Vec2, obstacles: List[Collider]):
    dist_to_closest = math.inf
    best_hiding_spot = Vec2()
    for o in obstacles:
        hiding_spot = get_hiding_position(o.pos, o.radius, target_pos)
        dist = (hiding_spot - position).length_squared()
        if dist < dist_to_closest:
            dist_to_closest = dist
            best_hiding_spot = hiding_spot
    if dist_to_closest == math.inf:
        return evade(target_pos, target_vel, position, max_speed, velocity)
    return arrive(position, best_hiding_spot, max_speed, velocity, Deceleration.fast)

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

def point_to_local_space(point, heading, side, position):
    """
    point: pygame.Vector2 (world space point)
    heading: pygame.Vector2 (vehicle forward direction, normalized)
    side: pygame.Vector2 (vehicle side/right vector, normalized)
    position: pygame.Vector2 (vehicle position)
    """
    # Translation: move point relative to vehicle
    trans = point - position

    # Create a local 2x2 transform basis:
    # [ heading.x  side.x ]
    # [ heading.y  side.y ]
    # Multiply trans by the transpose to convert to local coordinates
    local_x = trans.dot(heading)
    local_y = trans.dot(side)

    return pygame.Vector2(local_x, local_y)

def vector_to_world_space(local_vec, heading, side):
    """
    Convert a local direction vector into world space.
    heading: pygame.Vector2 (vehicle forward)
    side: pygame.Vector2 (vehicle right)
    """
    # Equivalent to multiplying by the vehicle's orientation matrix:
    # [ heading.x  side.x ]
    # [ heading.y  side.y ]

    x = local_vec.x * heading.x + local_vec.y * side.x
    y = local_vec.x * heading.y + local_vec.y * side.y
    return pygame.Vector2(x, y)
