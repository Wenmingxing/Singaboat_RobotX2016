#!/usr/bin/env python

""" movebase loiter

    Command a robot to move in a polygon around a centerpoint,
    inspired from moos-ivp loiter behavior

    borrowed from rbx1 move base square

    Ren Ye
    2016-09-30

    # changelog
    @2016-10-19: class inheritate from movebaseutil

"""

import rospy
import actionlib
from actionlib_msgs.msg import *
from geometry_msgs.msg import Pose, Point, Quaternion, Twist
from nav_msgs.msg import Odometry
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from tf.transformations import quaternion_from_euler, euler_from_quaternion
from visualization_msgs.msg import Marker
from math import pi, sin, cos, atan2
from move_base_util import MoveBaseUtil
# import thread


class Loiter(MoveBaseUtil):
    # initialize boat pose param

    def __init__(self, nodename, target=[10,0,0], radius=5, polygon=6, is_ccw=True, is_relative=True):
        MoveBaseUtil.__init__(self, nodename)

        self.loiter = {}
        self.mode = rospy.get_param("~mode", 1)
        self.mode_param = rospy.get_param("~mode_param", 2)
 	self.target = Point(rospy.get_param("~target_x", target[0]), rospy.get_param("~target_y", target[1]), 0)
	self.loiter["radius"] = rospy.get_param("~radius", radius) #double
        self.loiter["polygon"] = rospy.get_param("~polygon", polygon) #int
	self.loiter["is_ccw"] = rospy.get_param("~is_ccw", is_ccw) #bool
	self.loiter["is_relative"] = rospy.get_param("~is_relative", is_relative) #bool


        # find the target
        if self.loiter["is_relative"]:
            self.loiter["center"], self.loiter["heading"] = \
                self.convert_relative_to_absolute([self.target.x, self.target.y])
        else:  # absolute
            # obtained from vision nodes, absolute catersian
            # but may be updated later, so need to callback
            self.loiter["center"] = (self.target.x, self.target.y, self.target.z)  # (x, y, 0)

            # heading from boat to center
            self.loiter["heading"] = atan2(self.target.y - self.y0, self.target.x - self.x0)

        # create waypoints
        waypoints = self.create_waypoints()

        # # Initialize the visualization markers for RViz
        # self.init_markers()

        # Set a visualization marker at each waypoint
        for waypoint in waypoints:
            p = Point()
            p = waypoint.position
            self.markers.points.append(p)

        # # Subscribe to the move_base action server
        # self.move_base = actionlib.SimpleActionClient("move_base", MoveBaseAction)

        # rospy.loginfo("Waiting for move_base action server...")

        # # Wait 60 seconds for the action server to become available
        # self.move_base.wait_for_server(rospy.Duration(60))

        # rospy.loginfo("Connected to move base server")
        # rospy.loginfo("Starting navigation test")

        # Initialize a counter to track waypoints
        i = 0

        # Cycle through the waypoints
        while i <= self.loiter["polygon"] and not rospy.is_shutdown():
            # Update the marker display
            self.marker_pub.publish(self.markers)

            # Intialize the waypoint goal
            goal = MoveBaseGoal()

            # Use the map frame to define goal poses
            goal.target_pose.header.frame_id = 'map'

            # Set the time stamp to "now"
            goal.target_pose.header.stamp = rospy.Time.now()

            # Set the goal pose to the i-th waypoint
            goal.target_pose.pose = waypoints[i]

            # Start the robot moving toward the goal
            self.move(goal, self.mode, self.mode_param)

            i += 1
        else:  # escape loiter and continue to the next waypoint
            print "task finished"

    def create_waypoints(self):

        # Create a list to hold the target quaternions (orientations)
        quaternions = list()

        # First define the corner orientations as Euler angles
        # then calculate the position wrt to the center
        # need polar to catersian transform
        # print self.loiter["heading"]
        if self.loiter["is_ccw"]:  # counterclockwise
            # position theta related to center point with heading,
            # - pi is looking back from buoy to boat
            position_theta = [2 * pi * i / self.loiter["polygon"] - pi +
                              self.loiter["heading"]
                              for i in range(self.loiter["polygon"])]
            euler_angles = [i + pi / 2 for i in position_theta]
        else:  # clockwise
            position_theta = [2 * pi * i / self.loiter["polygon"] - pi -
                              self.loiter["heading"]
                              for i in reversed(range(self.loiter["polygon"]))]
            euler_angles = [i - pi / 2 for i in position_theta]

        # Then convert the angles to quaternions
        for angle in euler_angles:
            q_angle = quaternion_from_euler(0, 0, angle)
            q = Quaternion(*q_angle)
            quaternions.append(q)

        # Create a list to hold the waypoint poses
        waypoints = list()
        catersian_x = [self.loiter["radius"] * cos(theta) + self.loiter["center"][0]
                       for theta in position_theta]
        catersian_y = [self.loiter["radius"] * sin(theta) + self.loiter["center"][1]
                       for theta in position_theta]

        # close the loiter by append the quaternion/catersians' start to end
        quaternions.append(quaternions[0])
        catersian_x.append(catersian_x[0])
        catersian_y.append(catersian_y[0])

        # Append the waypoints to the list.  Each waypoint
        # is a pose consisting of a position and orientation in the map frame.
        for i in range(self.loiter["polygon"] + 1):
            waypoints.append(Pose(Point(catersian_x[i], catersian_y[i], 0.0),
                             quaternions[i]))
        # return the resultant waypoints
        return waypoints

    def odom_callback(self, msg):
        """ call back to subscribe, get odometry data:
        pose and orientation of the current boat,
        suffix 0 is for origin """
        self.x0 = msg.pose.pose.position.x
        self.y0 = msg.pose.pose.position.y
        self.z0 = msg.pose.pose.position.z
        x = msg.pose.pose.orientation.x
        y = msg.pose.pose.orientation.y
        z = msg.pose.pose.orientation.z
        w = msg.pose.pose.orientation.w
        self.roll0, self.pitch0, self.yaw0 = euler_from_quaternion((x, y, z, w))
        self.odom_received = True
        # rospy.loginfo([self.x0, self.y0, self.z0])


if __name__ == '__main__':
    try:
        Loiter(nodename="loiter_test")

    except rospy.ROSInterruptException:
        rospy.loginfo("Navigation test finished.")
