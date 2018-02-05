#!/usr/bin/python

from PIL import Image, ImageDraw
import numpy as np
import sys
import getopt


def raster_line(x0, y0, x1, y1):
    """Return numpy array of integer coordinates on the line
    from (x0, y0) to (x1, y1). Input coordinates should be integers.
    The result will contain both the start and the end point.
    Adapted from https://github.com/encukou/bresenham.
    """
    dx = x1 - x0
    dy = y1 - y0

    xsign = 1 if dx > 0 else -1
    ysign = 1 if dy > 0 else -1

    dx = abs(dx)
    dy = abs(dy)

    if dx > dy:
        xx, xy, yx, yy = xsign, 0, 0, ysign
    else:
        dx, dy = dy, dx
        xx, xy, yx, yy = 0, ysign, xsign, 0

    D = 2 * dy - dx
    y = 0

    pixels = np.empty([dx + 1, 2], dtype=np.uint16)

    for x in range(dx + 1):
        pixels[x, 0] = x0 + x * xx + y * yx
        pixels[x, 1] = y0 + x * xy + y * yy
        if D > 0:
            y += 1
            D -= dx
        D += dy
    return pixels


def rotation_matrix(alpha):
    """Return the rotation matrix for angle alpha"""
    angle = np.radians(alpha)
    c, s = np.cos(angle), np.sin(angle)
    R = [[c, -s], [s, c]]
    return R


class Point:
    """Holds a 2D point"""
    def __init__(self, x, y, index):
        self.x = x
        self.y = y
        self.index = index


class Circle:
    """Holds a circle consisting of points around a center"""
    def __init__(self, center_x, center_y, radius, num_points):
        self.angle = 0
        self.center_x = center_x
        self.center_y = center_y
        self.radius = radius
        self.step = 360 / num_points
        self.points = []
        self.index = 0
        self.all_lines = {}
        while (self.angle < 359.99):
            rotated = np.add(np.dot(rotation_matrix(self.angle), [0, self.radius]), [
                             self.center_x, self.center_y])
            self.points.append(
                Point(int(rotated.round()[0]), int(rotated.round()[1]), self.index))
            self.angle += self.step
            self.index += 1

    def get_xy(self, index):
        return (self.points[index].x, self.points[index].y)


def line_weight(image, line):
    """Returns the 'weight', i.e. the total amount of 'blackness' of a line"""
    summe = len(line) * 255 - np.sum(image[line[:, 1], line[:, 0]])
    summe /= len(line)
    return summe


def change_brightness(image, line):
    """Brightens a line in the image by a fixed amount"""
    for pixel in line:
        value = image[pixel[1]][pixel[0]]
        value += 50
        if value > 255:
            value = 255
        image[pixel[1]][pixel[0]] = value


def pair(a, b):
    """Holds a pair of points. Gets appended to the list of used points."""
    if a < b:
        return str(a) + "-" + str(b)
    else:
        return str(b) + "-" + str(a)


def lines_list(steps, image, circle, usedpoints, pointslist, mdiff):
    """The main algorithm. Iteratively finds the next best point to 
    approximate the image. 
    """
    loops = 0
    startpoint = circle.points[0]
    while loops < steps:
        max_weight = 0
        for point in circle.points:
            difference = abs(point.index - startpoint.index)
            # Note that the array wraps around w.r.t. the minimum difference
            if difference < mdiff or difference > (len(circle.points) - mdiff):
                continue
            weight = line_weight(image, circle.all_lines[
                                pair(startpoint.index, point.index)])
            if (weight > max_weight and
                point is not startpoint and
                    pair(startpoint.index, point.index) not in usedpoints):
                max_weight = weight
                nextpoint = point
                maxline = circle.all_lines[pair(startpoint.index, point.index)]
        usedpoints.append(pair(startpoint.index, nextpoint.index))
        pointslist.append([startpoint.index, nextpoint.index])
        change_brightness(image, maxline)
        startpoint = nextpoint
        loops += 1


def draw(pointslist, circle, size):
    im = Image.new('RGB', (size, size), (255, 255, 255))
    draw = ImageDraw.Draw(im, 'RGBA')
    for pair in pointslist:
        draw.line(circle.get_xy(pair[0]) +
                  circle.get_xy(pair[1]), fill=(0, 0, 0, 75))
    return im


def main(argv):
    input_file = 'selfie.jpg'
    image_size = 400
    number_of_threads = 1000
    minimum_difference = 20
    number_of_pins = 200
    outputimage_size = 400
    helpString = "aNewWayToKnit.py -i <input_file> -n <number_of_pins> -s <outputimage_size> -t <number_of_threads> -m <minimum_difference>"
    try:
        opts, args = getopt.getopt(
            argv, "hi:n:s:t:m:", ["input=", "number_of_pins=", "outputimage_size=", "number_of_threads=", "minimum_difference="])
    except getopt.GetoptError:
        print(helpString)
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print(helpString)
            sys.exit()
        elif opt in ("-i", "--input"):
            input_file = arg
        elif opt in ("-n", "--number_of_pins"):
            number_of_pins = int(arg)
        elif opt in ("-s", "--image_size"):
            outputimage_size = int(arg)
        elif opt in ("-t", "--number_of_threads"):
            number_of_threads = int(arg)
        elif opt in ("-m", "--minimum_difference"):
            minimum_difference = int(arg)
    print('input is = ', input_file)
    print('number_of_pins is = ', number_of_pins)
    

    try:
        input_image = Image.open(input_file)
    except FileNotFoundError:
        print("Please specify a valid image with option '-i'")
        sys.exit(2)
    if input_image.size[0] != input_image.size[1]:
        print("Please provide a square image.")
        sys.exit()
    if input_image.size[0] > 0:
        image_size = input_image.size[0]
    if outputimage_size == 0:
        outputimage_size = image_size
    input_image = input_image.convert("L")
    input_image = np.asarray(input_image)
    input_image.flags.writeable = True

    circle = Circle(image_size // 2, image_size // 2,
                    image_size // 2 - 1, number_of_pins)

    # Create a dict with all possible lines for faster calculation 
    circle.all_lines = {pair(i, j): raster_line(*circle.get_xy(i), *circle.get_xy(j))
                       for i in range(0, number_of_pins) for j in range(i + 1, number_of_pins)}

    # Empty arrays for used points
    usedpoints = []
    pointslist = []

    # Execute the main algorithm
    lines_list(number_of_threads, input_image, circle,
              usedpoints, pointslist, minimum_difference)

    # Circle for output
    outputcircle = Circle(outputimage_size // 2, outputimage_size //
                          2, outputimage_size // 2 - 1, number_of_pins)

    # Draw the output image
    outputimage = draw(pointslist, outputcircle, outputimage_size)
    outputimage.save('out.png')

    # Save the list of points
    with open("points.txt", 'wb') as outfile:
        np.savetxt(outfile, np.asarray(pointslist)[:, 1], fmt='%d,')


if __name__ == "__main__":
    main(sys.argv[1:])
