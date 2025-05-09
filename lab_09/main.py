import sys
from time import time

from typing import List

from PyQt5 import QtWidgets
from PyQt5 import uic
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsLineItem, QGraphicsEllipseItem, QGraphicsTextItem, QColorDialog
from PyQt5.QtGui import QWheelEvent, QMouseEvent, QPen, QColor, QKeyEvent

from dialogs import show_author, show_task, show_instruction, show_war_win
from class_point import Point
from cut_algs import check_convexity_polygon, sutherland_hodgman

grid_lines: List[QGraphicsLineItem] = []
max_win_size: List[int] = [0, 0, 0]
segments: List[List[Point]] = []
cutoff_figure_points: List[Point] = []
polygon_points: List[Point] = []
pinned_edge: List[Point] = []

scale: float = 1.0

is_pressed: bool = False
dragging: bool = False
enter_cutoff: bool = False
enter_vert_segment: bool = False
enter_hor_segment: bool = False
enter_pinned_point: bool = False

last_pos: QPoint = None
current_polygon_color: QColor = QColor(255, 0, 0)
current_cutoff_figure_color: QColor = QColor(0, 0, 255)
cutted_figure_color: QColor = QColor(0, 255, 0)

tmp_vert_segment: QGraphicsLineItem = None
tmp_hor_segment: QGraphicsLineItem = None


def change_polygon_color() -> None:
    colour = QColorDialog.getColor(initial=current_polygon_color)
    if colour.isValid():
        if colour.getRgb() != current_cutoff_figure_color.getRgb():
            set_polygon_color(QColor(colour))
        else:
            show_war_win(
                "Цвет отсекателя и отсекаемого многоугольника не могут совпадать.")


def set_polygon_color(color: QColor) -> None:
    global current_polygon_color
    current_polygon_color = color


def set_cutoff_color(color: QColor) -> None:
    global current_cutoff_figure_color
    current_cutoff_figure_color = color


def change_cutoff_color() -> None:
    colour = QColorDialog.getColor(initial=current_cutoff_figure_color)
    if colour.isValid():
        if colour.getRgb() != current_polygon_color.getRgb():
            set_cutoff_color(QColor(colour))
        else:
            show_war_win("Цвет отсекателя и отрезков не могут совпадать.")


def connect_to_edge(item):
    global pinned_edge
    global enter_pinned_point
    enter_pinned_point = True if not enter_pinned_point else False
    unpacked_segment = item.text().split(' <-> ')
    p1_str = unpacked_segment[0][1:-1].split(',')
    p2_str = unpacked_segment[1][1:-1].split(',')
    pinned_edge = [Point(float(p1_str[0]), float(p1_str[1])),
                   Point(float(p2_str[0]), float(p2_str[1]))]


class Ui(QtWidgets.QMainWindow):
    def __init__(self):
        super(Ui, self).__init__()
        uic.loadUi("./template.ui", self)  # временно в корне

        self.scene = QGraphicsScene()
        self.graphicsView.setScene(self.scene)

        self.need_grid()

        self.add_grid()

        # menu bar
        self.about_author.triggered.connect(show_author)
        self.about_task.triggered.connect(show_task)
        self.instruction.triggered.connect(show_instruction)

        self.clear_button.clicked.connect(self.clear_scene)

        self.graphicsView.setMouseTracking(True)

        # push buttons
        self.add_cutoff_button.clicked.connect(self.add_cutoff)
        self.change_cutoff_color_button.clicked.connect(change_cutoff_color)
        self.change_polygon_color_button.clicked.connect(change_polygon_color)
        self.cutoff_button.clicked.connect(self.cutoff)
        self.close_figure_button.clicked.connect(self.close_figure)

        # graphics view mouse events
        self.graphicsView.mousePressEvent = self.mousePressEvent
        self.graphicsView.wheelEvent = self.wheel_event
        self.graphicsView.mouseReleaseEvent = self.mouseReleaseEvent
        self.graphicsView.mouseMoveEvent = self.mouseMoveEvent

        # QListWidget events
        self.edges_list.itemClicked.connect(connect_to_edge)

        self.show()

    def wheel_event(self, event: QWheelEvent) -> None:
        global scale
        factor = 1.2

        if event.angleDelta().y() > 0:
            self.graphicsView.scale(factor, factor)
        else:
            self.graphicsView.scale(1.0 / factor, 1.0 / factor)

        # Получаем текущий масштаб по оси X (и Y)
        scale = self.graphicsView.transform().m11()
        if self.need_grid():
            for grid_line in grid_lines:
                if grid_line in self.scene.items():
                    self.scene.removeItem(grid_line)
            self.add_grid()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        global is_pressed, dragging, enter_vert_segment, enter_hor_segment, enter_pinned_point
        if event.button() == Qt.LeftButton:
            if enter_pinned_point:
                enter_pinned_point = False
                self.add_point_to_edge(event)
            elif not dragging and not enter_cutoff:
                self.add_point_figure(event, False)
            elif not dragging and enter_cutoff:
                self.add_point_figure(event, True)
            enter_vert_segment = False
            enter_hor_segment = False
            dragging = False
            is_pressed = False

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        global last_pos, dragging
        if is_pressed:
            dragging = True
            if enter_cutoff:
                if len(cutoff_figure_points) == 0:
                    last_scene_pos = self.graphicsView.mapToScene(last_pos)
                    last_scene_pos = Point(
                        last_scene_pos.x(), -last_scene_pos.y())
                else:
                    last_scene_pos = cutoff_figure_points[-1]
            else:
                if len(polygon_points) == 0:
                    last_scene_pos = self.graphicsView.mapToScene(last_pos)
                    last_scene_pos = Point(
                        last_scene_pos.x(), -last_scene_pos.y())
                else:
                    last_scene_pos = polygon_points[-1]
            cur_scene_pos = self.graphicsView.mapToScene(event.pos())
            if enter_vert_segment:
                global tmp_vert_segment
                if tmp_vert_segment:
                    self.scene.removeItem(tmp_vert_segment)
                    segments.pop()
                tmp_vert_segment = QGraphicsLineItem(last_scene_pos.x, -last_scene_pos.y,
                                                     cur_scene_pos.x(), -last_scene_pos.y)
                if enter_cutoff:
                    tmp_vert_segment.setPen(current_cutoff_figure_color)
                else:
                    tmp_vert_segment.setPen(current_polygon_color)
                self.scene.addItem(tmp_vert_segment)
                segments.append([Point(last_scene_pos.x, last_scene_pos.y),
                                 Point(cur_scene_pos.x(), last_scene_pos.y)])

            elif enter_hor_segment:
                global tmp_hor_segment
                if tmp_hor_segment:
                    self.scene.removeItem(tmp_hor_segment)
                    segments.pop()
                tmp_hor_segment = QGraphicsLineItem(last_scene_pos.x, -last_scene_pos.y,
                                                    last_scene_pos.x, cur_scene_pos.y())
                if enter_cutoff:
                    tmp_hor_segment.setPen(current_cutoff_figure_color)
                else:
                    tmp_hor_segment.setPen(current_polygon_color)
                self.scene.addItem(tmp_hor_segment)
                segments.append([Point(last_scene_pos.x, last_scene_pos.y),
                                 Point(last_scene_pos.x, -cur_scene_pos.y())])
            else:
                dx = event.pos().x() - last_pos.x()
                dy = event.pos().y() - last_pos.y()
                self.graphicsView.horizontalScrollBar().setValue(
                    self.graphicsView.horizontalScrollBar().value() - dx)
                self.graphicsView.verticalScrollBar().setValue(
                    self.graphicsView.verticalScrollBar().value() - dy)
                last_pos = event.pos()
                if self.need_grid():
                    for grid_line in grid_lines:
                        if grid_line in self.scene.items():
                            self.scene.removeItem(grid_line)
                    self.add_grid()
        scene_pos = self.graphicsView.mapToScene(event.pos())
        self.current_coords_label.setText(
            f'x :{scene_pos.x():.2f}, y :{-scene_pos.y():.2f}')

    def mousePressEvent(self, event: QMouseEvent) -> None:
        global last_pos, is_pressed
        if event.button() == Qt.LeftButton:
            is_pressed = True
            last_pos = event.pos()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        global enter_vert_segment, enter_hor_segment
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_Control:
            enter_vert_segment = True
            enter_hor_segment = False
        elif event.key() == Qt.Key_Shift:
            enter_hor_segment = True
            enter_vert_segment = False
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        global enter_vert_segment, enter_hor_segment, tmp_vert_segment, tmp_hor_segment
        if event.key() == Qt.Key_Control:
            enter_vert_segment = False
            if len(segments) > 0:
                vert_segment = segments.pop()
                self.scene.removeItem(tmp_vert_segment)
                self.draw_figure_point(vert_segment[1], enter_cutoff)
            tmp_vert_segment = None
        elif event.key() == Qt.Key_Shift:
            enter_hor_segment = False
            if len(segments) > 0:
                hor_segment = segments.pop()
                self.scene.removeItem(tmp_hor_segment)
                self.draw_figure_point(hor_segment[1], enter_cutoff)
            tmp_hor_segment = None
        else:
            super().keyReleaseEvent(event)

    def need_grid(self) -> bool:
        global max_win_size
        flag: bool = False
        max_size = self.graphicsView.maximumSize()
        max_width = int(max_size.width() * (1 / scale))
        max_height = int(max_size.height() * (1 / scale))
        grid_interval = int(50 * (1 / scale))
        grid_interval = round(grid_interval / 50) * 50
        if grid_interval != max_win_size[2]:
            max_win_size[2] = grid_interval
            flag = True
        if max_win_size[0] < max_width and max_win_size[1] < max_height:
            max_win_size[0] = max_width
            max_win_size[1] = max_height
            flag = True
        return flag

    def add_grid(self) -> None:
        global grid_lines, max_win_size
        max_width = max_win_size[0]
        max_height = max_win_size[1]
        grid_interval = max_win_size[2]
        if grid_interval == 0:
            grid_interval = 20
        self.current_grid_label.setText(f'Текущий шаг сетки: {grid_interval}')
        start_grid_width = - ((max_width // 2) +
                              grid_interval - (max_width // 2) % grid_interval)
        start_grid_height = - \
            ((max_height // 2) + grid_interval - (max_height // 2) % grid_interval)
        end_grid_width = (max_width // 2) - (max_width // 2) % grid_interval
        end_grid_height = (max_height // 2) - (max_width // 2) % grid_interval
        pen = QPen(Qt.darkGray)
        pen_width = 1 if int(1 / scale) == 0 else int(1 / scale)
        pen.setWidth(pen_width)
        for x in range(start_grid_width, end_grid_width, grid_interval):
            line = QGraphicsLineItem(x, start_grid_height, x, end_grid_height)
            line.setPen(pen)
            line.setZValue(0)
            grid_lines.append(line)
            self.scene.addItem(line)
        for y in range(start_grid_height, end_grid_height, grid_interval):
            line = QGraphicsLineItem(start_grid_width, y, end_grid_width, y)
            line.setPen(pen)
            line.setZValue(0)
            grid_lines.append(line)
            self.scene.addItem(line)

        axis_x = QGraphicsLineItem(-300 * (1 / scale), 0, 300 * (1 / scale), 0)
        axis_y = QGraphicsLineItem(0, -300 * (1 / scale), 0, 300 * (1 / scale))
        pen.setColor(Qt.white)
        grid_lines.append(axis_x)
        grid_lines.append(axis_y)
        axis_x.setPen(pen)
        axis_y.setPen(pen)
        axis_x.setZValue(0)
        axis_y.setZValue(0)
        self.scene.addItem(axis_x)
        self.scene.addItem(axis_y)

    def change_color(self, color: QColor) -> None:
        global current_polygon_color
        current_polygon_color = color
        objects = self.scene.items()
        for obj in objects:
            if obj not in grid_lines and not isinstance(obj, QGraphicsTextItem):
                obj.setPen(current_polygon_color)

    def clear_scene(self):
        for item in self.scene.items():
            if item not in grid_lines:
                self.scene.removeItem(item)
        self.scroll_list.clear()
        cutoff_figure_points.clear()
        self.edges_list.clear()
        polygon_points.clear()

    def close_figure(self, arg=None):
        global enter_cutoff
        if arg:
            if arg == 'set_cutoff':
                enter_cutoff = True
            else:
                enter_cutoff = False
        if not enter_cutoff:
            if len(polygon_points) < 3:
                show_war_win(
                    "Невозможно замкнуть отсекаемый многоугольник, задано слишком мало точек.")
                return
            self.update_figure_segments(is_cutoff=False, closing=True)
        else:
            if len(cutoff_figure_points) < 3:
                show_war_win(
                    "Невозможно замкнуть отсекатель, задано слишком мало точек.")
                return
            self.update_figure_segments(is_cutoff=True, closing=True)

    def add_point_figure(self, event: QMouseEvent, is_cutoff: bool) -> None:
        pos = event.pos()
        scene_pos = self.graphicsView.mapToScene(pos)
        p_x, p_y = scene_pos.x(), scene_pos.y()
        self.draw_figure_point(Point(p_x, -p_y), is_cutoff)

    def draw_figure_point(self, point: Point, is_cutoff: bool) -> None:
        scene_point = QGraphicsEllipseItem(
            point.x, -point.y, 5 * (1 / scale), 5 * (1 / scale))
        if is_cutoff:
            cutoff_figure_points.append(point)
            self.update_figure_segments(is_cutoff=True)
            scene_point.setBrush(current_cutoff_figure_color)
        else:
            polygon_points.append(point)
            self.update_figure_segments()
            scene_point.setBrush(current_polygon_color)
        self.scene.addItem(scene_point)

    def add_point_to_edge(self, event: QMouseEvent):
        pos = event.pos()
        scene_pos = self.graphicsView.mapToScene(pos)
        p_x = scene_pos.x()
        k = (pinned_edge[1].y - pinned_edge[0].y) / \
            (pinned_edge[1].x - pinned_edge[0].x)
        b = pinned_edge[1].y - k * pinned_edge[1].x
        y = b + k * p_x
        self.draw_figure_point(Point(p_x, y), False)

    def update_figure_segments(self, is_cutoff=False, closing=False):
        if is_cutoff:
            if closing:
                new_list_item = f'({cutoff_figure_points[-1].x}, {cutoff_figure_points[-1].y}) <->' \
                    f'({cutoff_figure_points[0].x}, {cutoff_figure_points[0].y})'
                if self.edges_list.item(self.edges_list.count() - 1).text() != new_list_item:
                    self.draw_line(
                        cutoff_figure_points[-1], cutoff_figure_points[0], current_cutoff_figure_color)
                    self.edges_list.addItem(f'({cutoff_figure_points[-1].x}, {cutoff_figure_points[-1].y}) <-> '
                                            f'({cutoff_figure_points[0].x}, {cutoff_figure_points[0].y})')
                    cutoff_figure_points.append(cutoff_figure_points[0])
                else:
                    show_war_win("Фигура уже замкнута.")
            elif len(cutoff_figure_points) >= 2:
                self.draw_line(
                    cutoff_figure_points[-1], cutoff_figure_points[-2], current_cutoff_figure_color)
                self.edges_list.addItem(f'({cutoff_figure_points[-2].x}, {cutoff_figure_points[-2].y}) <-> '
                                        f'({cutoff_figure_points[-1].x}, {cutoff_figure_points[-1].y})')
        else:
            if closing:
                new_list_item = f'({polygon_points[-1].x}, {polygon_points[-1].y}) <->' \
                    f' ({polygon_points[0].x}, {polygon_points[0].y})'
                if self.scroll_list.item(self.scroll_list.count() - 1).text() != new_list_item:
                    self.draw_line(
                        polygon_points[-1], polygon_points[0], current_polygon_color)
                    self.scroll_list.addItem(f'({polygon_points[-1].x}, {polygon_points[-1].y}) <-> '
                                             f'({polygon_points[0].x}, {polygon_points[0].y})')
                    polygon_points.append(polygon_points[0])
                else:
                    show_war_win("Фигура уже замкнута.")
            elif len(polygon_points) >= 2:
                self.draw_line(
                    polygon_points[-1], polygon_points[-2], current_polygon_color)
                self.scroll_list.addItem(f'({polygon_points[-2].x}, {polygon_points[-2].y}) <-> '
                                         f'({polygon_points[-1].x}, {polygon_points[-1].y})')

    def draw_line(self, p1: Point, p2: Point, color: QColor) -> None:
        line = QGraphicsLineItem(p1.x, -p1.y, p2.x, -p2.y)
        line.setPen(color)
        line.setZValue(1)
        self.scene.addItem(line)

    def set_new_colour(self) -> None:
        colour = QColorDialog.getColor(initial=current_polygon_color)
        if colour.isValid():
            self.change_color(QColor(colour))

    def add_cutoff(self) -> None:
        global enter_cutoff
        enter_cutoff = True if not enter_cutoff else False
        if enter_cutoff:
            self.add_cutoff_button.setText("Закончить добавление отсекателя")
        else:
            self.add_cutoff_button.setText("Добавить выпуклый отсекатель")

    def cutoff(self) -> None:
        if len(cutoff_figure_points) < 3:
            show_war_win("Не построен отсекатель!")
            return
        if enter_cutoff:
            show_war_win("Не окончен ввод отсекателя!")
            return
        if len(polygon_points) < 3:
            show_war_win("Не построен отсекатель!")
            return
        if not check_convexity_polygon(cutoff_figure_points):
            show_war_win("Отсекатель должен быть выпуклым!")
            return

        cutted_polygon_points = sutherland_hodgman(
            polygon_points, cutoff_figure_points)
        for i in range(len(cutted_polygon_points) - 1):
            self.draw_line(
                cutted_polygon_points[i], cutted_polygon_points[i + 1], cutted_figure_color)
        self.draw_line(
            cutted_polygon_points[-1], cutted_polygon_points[0], cutted_figure_color)


if __name__ == '__main__':
    global test_i
    start_testing = time()
    app = QtWidgets.QApplication(sys.argv)
    window = Ui()

    FUNC_TESTING = False
    if len(sys.argv) > 2:
        FUNC_TESTING = True
        test_i = int(sys.argv[1])
        num_cutoff_points = int(sys.argv[2])
        for _ in range(num_cutoff_points):
            px, py = float(sys.argv[2 * _ + 3]), float(sys.argv[2 * _ + 4])
            window.draw_figure_point(Point(px, py), True)
        window.close_figure('set_cutoff')
        num_polygon_points = int(sys.argv[2 * num_cutoff_points + 3])
        curr_ind = 2 * num_cutoff_points + 4
        for _ in range(num_polygon_points):
            px, py = float(sys.argv[curr_ind + 2 * _]
                           ), float(sys.argv[curr_ind + 2 * _ + 1])
            window.draw_figure_point(Point(px, py), False)
        window.close_figure('set_polygon')
        window.cutoff()

    if FUNC_TESTING:
        screenshot = window.grab()
        screenshot.save(f'./results/test_{test_i}.png', 'png')
    else:
        sys.exit(app.exec_())
