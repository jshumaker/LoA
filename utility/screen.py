__author__ = 'Jody Shumaker'

import math


class Color:
    def __init__(self, r, g, b, a=0):
        self.r = r
        self.g = g
        self.b = b
        self.a = a
        # Calculate the furthest distance a color could be from this color.
        self.max_distance = math.sqrt(
            (self.r if self.r > 128 else 255 - self.r)**2 +
            (self.g if self.g > 128 else 255 - self.g)**2 +
            (self.b if self.b > 128 else 255 - self.b)**2
        )

    def __str__(self):
        return "R{0:03d}G{1:03d}B{2:03d}A{3:03d}".format(int(self.r), int(self.g), int(self.b), int(self.a))

    def compare(self, color2):
        distance = math.sqrt((self.r - color2.r)**2 + (self.g - color2.g)**2 + (self.b - color2.b)**2)
        if distance < 1:
            distance = 1
        accuracy = (((self.max_distance - distance) / self.max_distance) ** 3)
        # Let's consider 20 % a rough floor. It's rare to get below that without looking at extremes
        accuracy = (accuracy - 0.20) / 0.8
        if accuracy < 0:
            accuracy = 0
        return accuracy


def get_pixel(image, x, y):
    r, g, b = image.getpixel((x, y))
    return Color(r, g, b, 0)


def get_avg_pixel(image, x, y, r=15):
    avgpixel = Color(0, 0, 0, 0)
    count = (r * 2) ** 2
    for posx in range(x - r, x + r):
        for posy in range(y - r, y + r):
            p = get_pixel(image, posx, posy)
            avgpixel.r += p.r / float(count)
            avgpixel.g += p.g / float(count)
            avgpixel.b += p.b / float(count)
            avgpixel.a += p.a / float(count)
    return avgpixel

def compare_images(i1, i2):
    rms = 0.0
    if i1.size != i2.size:
        raise ValueError("Image sizes for comparison do not match. {0} vs {1}".format(i1.size, i2.size))
    width, height = i1.size
    for x in range(width - 1):
        for y in range(height - 1):
            pixel1 = i1.getpixel((x, y))
            pixel2 = i2.getpixel((x, y))
            rms += math.sqrt((pixel1[0] - pixel2[0])**2 + (pixel1[1] - pixel2[1])**2 + (pixel1[2] - pixel2[2])**2)
    return rms