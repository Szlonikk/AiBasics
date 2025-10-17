from typing import List
from Collider import Collider
class Obstacles:

    def __init__(self,x,y,radius):
        self.collider = Collider(x, y, radius)

    def update(self, dt: float):
        print(123) 

    def draw(self):
        print(123)

    @staticmethod
    def generateObstacles() -> List["Obstacles"]:
        print(321)