
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

#-----------------BEHAVIOUR-------------------

# SEEK - returns a force that directs an agent toward a target position
def seek(position: Vec2, target: Vec2, max_speed: float, velocity: float) -> Vec2:
    desired = (target - position).normalize() * max_speed
    return desired - velocity

# FLEE - creates a force that steers the agent away
def flee(position: Vec2, target: Vec2, max_speed: float, velocity: float) -> Vec2:
    # only flee if the target is within 'panic distance'. Work in distance squared space.
    panicDistanceSq = ZOMBIE_PANIC_DISTANCE * ZOMBIE_PANIC_DISTANCE

    desired = position - target
    if desired.length_squared() > panicDistanceSq:
        return Vec2(0, 0)
    desired = desired.normalize() * max_speed
    return desired - velocity

# ARRIVE - steers the agent in such a way it decelerates onto the target position
def arrive(position: Vec2, target: Vec2, max_speed: float, velocity: float, deceleration: Deceleration):
    toTarget = target - position
    # calculate the distance to the target position
    dist = target.length()
    if dist > 0.0:
        # because Deceleration is enumerated as an int, this value is required 
        # to provide fine tweaking of the deceleration.
        decelerationTweaker = ZOMBIE_DECELERATION_TWEAKER
        # calculate the speed required to reach the target given the desired 
        # deceleration - make sure the velocity does not exceed the max
        speed = min(dist / (deceleration.value * decelerationTweaker), max_speed)
        # from here proceed just like Seek except we don't need to normalize 
        # the ToTarget vector because we have already gone to the trouble
        # of calculating its length: dist.
        desired = toTarget * speed / dist
        return desired - velocity
    return Vec2(0, 0)

# PURSUIT - predicts where evader is going to be in the future and runs toward that offset, making adjustments as it narrows the gap 
def pursuit(position: Vec2, heading: Vec2, evader: Vec2, evaderHeading: Vec2, evaderVelocity: Vec2, evaderSpeed: float, max_speed: float, velocity: float):
    # if the evader is ahead and facing the agent then we can just seek 
    # for the evader's current position.
    toEvader = evader - position
    relativeHeading = heading.dot(evaderHeading)
    if toEvader.dot(heading) > 0 and relativeHeading > -math.cos(ZOMBIE_FACING_ANGLE):
        return seek(position, evader, max_speed, velocity)
    
    # Not considered ahead so we predict where the evader will be.
    
    # the look-ahead time is proportional to the distance between the evader 
    # and the pursuer; and is inversely proportional to the sum of the
    # agents' velocities
    lookAheadTime = toEvader.length() / (max_speed + evaderSpeed)
    # now seek to the predicted future position of the evader
    return seek(position, evader + evaderVelocity * lookAheadTime, max_speed, velocity)

# EVADE - flees from the estimated future position
def evade(pursuer_pos: Vec2, pursuer_vel: Vec2, position: Vec2, max_speed: float, velocity: Vec2) -> Vec2:
    # the look-ahead time is proportional to the distance between the pursuer
    # and the evader; and is inversely proportional to the sum of the
    # agents' velocities
    to_pursuer = pursuer_pos - position
    pursuer_speed = pursuer_vel.length()
    look_ahead_time = to_pursuer.length() / (max_speed + pursuer_speed)
    # now flee away from predicted future position of the pursuer
    return flee(position, pursuer_pos + pursuer_vel * look_ahead_time, max_speed, velocity) 

# WANDER - gives the impression of a random walk through the agent’s environment
def wander(heading: Vec2, wander_target: Vec2) -> Tuple[Vec2, Vec2]:
    # first, add a small random vector to the target’s position (RandomClamped
    # returns a value between -1 and 1)
    jitter = ZOMBIE_WANDER_JITTER
    wander_target += Vec2(random.uniform(-1, 1) * jitter, random.uniform(-1, 1) * jitter)
    # reproject this new vector back onto a unit circle and
    # increase the length of the vector to the same as the radius
    # of the wander circle
    wander_target = wander_target.normalize() * ZOMBIE_WANDER_CIRCLE_RADIUS
    # project the target into world space
    circle_center = heading.normalize() * ZOMBIE_WANDER_CIRCLE_DISTANCE
    target_world = circle_center + wander_target
    return target_world, wander_target

# OBSTACLE_AVOIDANCE - steers a vehicle to avoid obstacles lying in its path
def obstacle_avoidance(me: Collider, velocity: Vec2, speed: float, max_speed: float, obstacles: List[Collider], look_ahead: float = 80.0) -> Vec2:
    # the detection box length is proportional to the agent's velocity
    boxLength = look_ahead + (speed / max_speed) * look_ahead
    # this will keep track of the closest intersecting obstacle (CIB)
    closest = None
    # this will be used to track the distance to the CIB
    closest_dist = math.inf

    # tag all obstacles within range of the box for processing
    for ob in obstacles:
            ob.tagged = False   # clear any previous tag

            # distance from vehicle to obstacle
            dist_sq = (ob.pos - me.pos).length_squared()

            if dist_sq < ZOMBIE_RADIUS * ZOMBIE_RADIUS:
                ob.tagged = True

    # variables needed to calculate obstacle's position in local space
    heading = Vec2(0, 0)
    if velocity.length() > 0.0:
        heading = velocity.normalize()
    side = (heading.y * -1, heading.x)

    for o in obstacles:
        # if the obstacle has been tagged within range proceed
        if o.tagged:
            # calculate this obstacle's position in local space
            localPos = point_to_local_space(o.pos, heading, side, me.pos)
            # if the local position has a negative x value then it must lay
            # behind the agent. (in which case it can be ignored)
            if localPos >= 0:
                #if the distance from the x axis to the object's position is less
                # than its radius + half the width of the detection box then there
                # is a potential intersection.
                expandedRadius = o.radius + ZOMBIE_RADIUS
                if abs(localPos.y) < expandedRadius:
                    # now to do a line/circle intersection test. The center of the
                    # circle is represented by (cX, cY). The intersection points are
                    # given by the formula x = cX +/-sqrt(r^2-cY^2) for y=0.
                    # We only need to look at the smallest positive value of x because
                    # that will be the closest point of intersection.
                    cX = localPos.x
                    cY = localPos.y
                    # we only need to calculate the sqrt part of the above equation once
                    sqrtPart = math.sqrt(expandedRadius * expandedRadius - cY * cY)
                    ip = cX - sqrtPart
                    if ip <= 0:
                        ip = cX + sqrtPart
                    # test to see if this is the closest so far. If it is, keep a
                    # record of the obstacle and its local coordinates
                    if ip < closest_dist:
                        closest_dist = ip
                        closest = o
    # if we have found an intersecting obstacle, calculate a steering
    # force away from it
    if closest:
        steeringForce = Vec2()
        # the closer the agent is to an object, the stronger the steering force 
        # should be
        multiplier = 1.0 + (boxLength - closest.pos.x) / boxLength
        # calculate the lateral force
        steeringForce.y = (closest.radius - closest.pos.y) * multiplier
        # apply a braking force proportional to the obstacle’s distance from 
        # the vehicle.
        steeringForce.x = (closest.radius - closest.pos.x) * ZOMBIE_BREAKING_WEIGHT
        # finally, convert the steering vector from local to world space
        return vector_to_world_space(steeringForce, heading, side)
    return Vec2(0, 0)

# WALL_AVOIDANCE - avoid potential collisions with a wall
def wall_avoidance(me: Collider, velocity: Vec2) -> Vec2:
    # Predict next position and push back from walls (acts like "bounce" intent)
    nudge = Vec2()
    future = me.pos + velocity * 0.4
    if future.x - me.radius < 0: nudge.x += 1
    if future.x + me.radius > WIDTH: nudge.x -= 1
    if future.y - me.radius < 0: nudge.y += 1
    if future.y + me.radius > HEIGHT: nudge.y -= 1
    return nudge * velocity.length()

# HIDE - sneak up on a player
def hide(position: Vec2, max_speed: float, velocity: Vec2, target_pos: Vec2, target_vel: Vec2, obstacles: List[Collider]):
    dist_to_closest = math.inf
    best_hiding_spot = Vec2()
    for o in obstacles:
        # calculate the position of the hiding spot for this obstacle
        hiding_spot = get_hiding_position(o.pos, o.radius, target_pos)
        # work in distance-squared space to find the closest hiding
        # spot to the agent
        dist = (hiding_spot - position).length_squared()
        if dist < dist_to_closest:
            dist_to_closest = dist
            best_hiding_spot = hiding_spot
    # if no suitable obstacles found then evade the target
    if dist_to_closest == math.inf:
        return evade(target_pos, target_vel, position, max_speed, velocity)
    # else use Arrive on the hiding spot
    return arrive(position, best_hiding_spot, max_speed, velocity, Deceleration.fast)

#---------------GROUP BEHAVIOURS------------------

# SEPARATION - creates a force that steers a vehicle away from those in its neighborhood region
def separation(me, neighbours: List) -> Vec2:
    force = Vec2()
    for n in neighbours:
        # make sure this agent isn't included in the calculations and that
        # the agent being examined is close enough.
        if n is not me and n.tagged: 
            to_me = me.collider.pos - n.collider.pos
            # scale the force inversely proportional to the agent's distance
            # from its neighbor.
            force += to_me.normalize() / to_me.length()
    return force

# ALIGNMENT - attempts to keep a vehicle’s heading aligned with its neighbors
def alignment(me, neighbours: List) -> Vec2:
    # used to record the average heading of the neighbors
    average_heading = Vec2()
    # used to count the number of vehicles in the neighborhood
    neighbour_count = 0.0
    # iterate through all the tagged vehicles and sum their heading vectors
    for n in neighbours:
        # make sure *this* agent isn't included in the calculations and that
        # the agent being examined is close enough
        if n is not me and n.tagged:
            average_heading += n.vel.normalize()
            neighbour_count += 1.0
    # if the neighborhood contained one or more vehicles, average their
    # heading vectors.
    if neighbour_count > 0.0:
        average_heading /= neighbour_count
        average_heading -= me.vel.normalize()
    return average_heading

# COHESION - produces a steering force that moves a vehicle toward the center of mass of its neighbors
def cohesion(me, max_speed: float, neighbours: List) -> Vec2:
    # first find the center of mass of all the agents
    center_of_mass = Vec2()
    force = Vec2()
    neighbour_count = 0.0
    # iterate through the neighbors and sum up all the position vectors
    for n in neighbours:
        # make sure *this* agent isn't included in the calculations and that
        # the agent being examined is a neighbor
        if n is not me and n.tagged:
            center_of_mass  += n.collider.pos
            neighbour_count += 1
    if neighbour_count > 0.0:
        # the center of mass is the average of the sum of positions
        center_of_mass /= neighbour_count
        # now seek toward that position
        force = seek(me.collider.pos, center_of_mass, max_speed, me.vel)
    return force

#--------------HELPER FUNCTIONS---------------

def truncate(v: Vec2, max_value: float) -> Vec2:
    if v.length_squared() > max_value * max_value:
        return v.normalize() * max_value
    return v

def get_hiding_position(pos_ob: Vec2, radius_ob: float, target_pos: Vec2) -> Vec2:
    # calculate how far away the agent is to be from the chosen obstacle’s 
    # bounding radius
    dist_away = radius_ob + ZOMBIE_DISTANCE_FROM_BOUNDARY
    # calculate the heading toward the object from the target
    to_ob = (pos_ob - target_pos).normalize()
    # scale it to size and add to the obstacle's position to get
    # the hiding spot.
    return (to_ob * dist_away) + pos_ob

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
