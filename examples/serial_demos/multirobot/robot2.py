from base_robot import BaseRobot


class Robot2(BaseRobot):
    def __init__(self, enabled=True):
        super(Robot2, self).__init__("multibot_robot_2", enabled)
