from lib_ip.Bbox import Bbox


def cvt_compos_relative_pos(compos, col_min_base, row_min_base):
    for compo in compos:
        compo.compo_relative_position(col_min_base, row_min_base)


class Component:
    def __init__(self, region):
        self.region = region
        self.boundary = self.compo_get_boundary()
        self.bbox = self.compo_get_bbox()

        self.region_area = len(region)
        self.width = len(self.boundary[0])
        self.height = len(self.boundary[2])
        self.area = self.width * self.height
        self.category = None

        self.rect_ = None
        self.line_ = None

    def put_bbox(self):
        return self.bbox.put_bbox()

    def compo_get_boundary(self):
        '''
        get the bounding boundary of an object(region)
        boundary: [top, bottom, left, right]
        -> up, bottom: (column_index, min/max row border)
        -> left, right: (row_index, min/max column border) detect range of each row
        '''
        border_up, border_bottom, border_left, border_right = {}, {}, {}, {}
        for point in self.region:
            # point: (row_index, column_index)
            # up, bottom: (column_index, min/max row border) detect range of each column
            if point[1] not in border_up or border_up[point[1]] > point[0]:
                border_up[point[1]] = point[0]
            if point[1] not in border_bottom or border_bottom[point[1]] < point[0]:
                border_bottom[point[1]] = point[0]
            # left, right: (row_index, min/max column border) detect range of each row
            if point[0] not in border_left or border_left[point[0]] > point[1]:
                border_left[point[0]] = point[1]
            if point[0] not in border_right or border_right[point[0]] < point[1]:
                border_right[point[0]] = point[1]

        boundary = [border_up, border_bottom, border_left, border_right]
        # descending sort
        for i in range(len(boundary)):
            boundary[i] = [[k, boundary[i][k]] for k in boundary[i].keys()]
            boundary[i] = sorted(boundary[i], key=lambda x: x[0])
        return boundary

    def compo_get_bbox(self):
        """
        Get the top left and bottom right points of boundary
        :param boundaries: boundary: [top, bottom, left, right]
                            -> up, bottom: (column_index, min/max row border)
                            -> left, right: (row_index, min/max column border) detect range of each row
        :return: corners: [(top_left, bottom_right)]
                            -> top_left: (column_min, row_min)
                            -> bottom_right: (column_max, row_max)
        """
        col_min, row_min = (int(min(self.boundary[0][0][0], self.boundary[1][-1][0])), int(min(self.boundary[2][0][0], self.boundary[3][-1][0])))
        col_max, row_max = (int(max(self.boundary[0][0][0], self.boundary[1][-1][0])), int(max(self.boundary[2][0][0], self.boundary[3][-1][0])))
        bbox = Bbox(col_min, row_min, col_max, row_max)
        return bbox

    def compo_is_rectangle(self, min_rec_evenness, max_dent_ratio):
        '''
        detect if an object is rectangle by evenness and dent of each border
        '''
        dent_direction = [1, -1, 1, -1]  # direction for convex

        flat = 0
        parameter = 0
        for n, border in enumerate(self.boundary):
            parameter += len(border)
            # dent detection
            pit = 0  # length of pit
            depth = 0  # the degree of surface changing
            if n <= 1:
                adj_side = max(len(self.boundary[2]), len(self.boundary[3]))  # get maximum length of adjacent side
            else:
                adj_side = max(len(self.boundary[0]), len(self.boundary[1]))

            # -> up, bottom: (column_index, min/max row border)
            # -> left, right: (row_index, min/max column border) detect range of each row
            abnm = 0
            for i in range(3, len(border) - 1):
                # calculate gradient
                difference = border[i][1] - border[i + 1][1]
                # the degree of surface changing
                depth += difference
                # ignore noise at the start of each direction
                if i / len(border) < 0.08 and (dent_direction[n] * difference) / adj_side > 0.5:
                    depth = 0  # reset

                # print(border[i][1], i / len(border), depth, (dent_direction[n] * difference) / adj_side )
                # if the change of the surface is too large, count it as part of abnormal change
                if abs(depth) / adj_side > 0.3:
                    abnm += 1  # count the size of the abnm
                    # if the abnm is too big, the shape should not be a rectangle
                    if abnm / len(border) > 0.1:
                        self.rect_ = False
                        return False
                    continue
                else:
                    # reset the abnm if the depth back to normal
                    abnm = 0

                # if sunken and the surface changing is large, then counted as pit
                if dent_direction[n] * depth < 0 and abs(depth) / adj_side > 0.15:
                    pit += 1
                    continue

                # if the surface is not changing to a pit and the gradient is zero, then count it as flat
                if abs(depth) < 7:
                    flat += 1
                # print(depth, adj_side, abnm)
            # if the pit is too big, the shape should not be a rectangle
            if pit / len(border) > max_dent_ratio:
                self.rect_ = False
                return False
            # print()
        # print(flat / parameter, '\n')
        # draw.draw_boundary([boundary], org_shape, show=True)
        # ignore text and irregular shape
        if (flat / parameter) < min_rec_evenness:
            self.rect_ = False
            return False
        self.rect_ = True
        return True

    def compo_is_line(self, min_line_thickness):
        """
        Check this object is line by checking its boundary
        :param boundary: boundary: [border_top, border_bottom, border_left, border_right]
                                    -> top, bottom: list of (column_index, min/max row border)
                                    -> left, right: list of (row_index, min/max column border) detect range of each row
        :param min_line_thickness:
        :return: Boolean
        """
        # horizontally
        slim = 0
        for i in range(self.width):
            if abs(self.boundary[1][i][1] - self.boundary[0][i][1]) <= min_line_thickness:
                slim += 1
        if slim / len(self.boundary[0]) > 0.93:
            self.line_ = True
            return True
        # vertically
        slim = 0
        for i in range(self.height):
            if abs(self.boundary[2][i][1] - self.boundary[3][i][1]) <= min_line_thickness:
                slim += 1
        if slim / len(self.boundary[2]) > 0.93:
            self.line_ = True
            return True
        self.line_ = False
        return False

    def compo_relation(self, compo_b):
        """
        :return: -1 : a in b
                 0  : a, b are not intersected
                 1  : b in a
                 2  : a, b are identical or intersected
        """
        return self.bbox.bbox_relation(compo_b.bbox)

    def compo_relative_position(self, col_min_base, row_min_base):
        '''
        Convert to relative position based on base coordinator
        '''
        self.bbox.bbox_cvt_relative_position(col_min_base, row_min_base)

    def compo_merge(self, compo_b):
        self.bbox = self.bbox.bbox_merge(compo_b.bbox)