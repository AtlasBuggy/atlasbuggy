from base_robot import BaseRobot


class Robot1(BaseRobot):
    def __init__(self, enabled=True):
        super(Robot1, self).__init__("multibot_robot_1", enabled)
