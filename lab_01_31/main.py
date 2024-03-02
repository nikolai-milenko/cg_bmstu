import sys

from PyQt5 import QtWidgets
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPen, QBrush, QMouseEvent
from PyQt5.QtWidgets import QMessageBox, QGraphicsScene, QGraphicsEllipseItem, QGraphicsLineItem

from triangle_methods import *

point_list = []
scene_point_list = []
grid_lines = []
point_scale = []

scale = 1
max_win_size = [0, 0, 0]

dragging = False
last_pos = None


def show_war_win(war):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Warning)
    msg.setText(war)
    msg.setWindowTitle("Предупреждение!")
    msg.exec_()


def show_err_win(err):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setText(err)
    msg.setWindowTitle("Ошибка!")
    msg.exec_()


def show_author():
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Information)
    msg.setWindowTitle("Об авторе")
    msg.setText(f"Лабораторная работа №1.\nРазработал Миленко Николай ИУ7-45Б")
    msg.exec_()


def show_task():
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Information)
    msg.setWindowTitle("Условие задачи")
    msg.setText(f"На плоскости дано множество точек.\n\nНайти такой треугольник с вершинами в этих точках, "
                f"у которого угол, образованный высотой и медианой, исходящими из одной вершины, минимален.\n\n"
                f"Вывести изображение в графическом режиме.\n\n31 Вариант.")
    msg.exec_()


def check_one_line():
    koeff_1 = (point_list[1].y - point_list[0].y) * (point_list[2].x - point_list[1].x)
    koeff_2 = (point_list[2].y - point_list[1].y) * (point_list[1].x - point_list[0].x)
    if abs(koeff_1 - koeff_2) < EPS:
        print(koeff_1, koeff_2)
        return True
    return False


def solve_task():
    coord_start, coord_perpend, coord_median = None, None, None
    min_angle = 180
    ans_vertex = []

    if not point_list or len(point_list) < 3:
        show_err_win("Недостаточно точек для решения задачи.\nДобавьте хотя бы 3 точки.")
        return
    if check_one_line():
        show_err_win("Невозможно построить треугольник.\nТочки лежат на одной прямой.")
        return

    for i in range(len(point_list) - 2):
        for j in range(i + 1, len(point_list) - 1):
            for k in range(j + 1, len(point_list)):
                pa = point_list[i]
                pb = point_list[j]
                pc = point_list[k]

                print(f"\n------ Points Triangle --------")
                print(f"pa = {pa.x, pa.y}\npb = {pb.x, pb.y}\npc = {pc.x, pc.y}")

                side_1 = side_len(pa, pb)
                side_2 = side_len(pa, pc)
                side_3 = side_len(pb, pc)
                print("----------Len Sides --------")
                print(side_1, side_2, side_3)

                if not is_triangle(side_1, side_2, side_3):
                    continue

                print("------Main vertex - pa:")
                pm_i, pp_i, angle_i = find_corner(pa, pb, pc)
                print("------ Main vertex - pb:")
                pm_j, pp_j, angle_j = find_corner(pb, pa, pc)
                print("------ Main vertex - pc:")
                pm_k, pp_k, angle_k = find_corner(pc, pb, pa)

                cur_min_angle = min(angle_i, angle_j, angle_k)
                if min_angle > cur_min_angle:
                    ans_vertex = [pa, pb, pc]
                    min_angle = cur_min_angle
                    if abs(angle_i - min_angle) < EPS:
                        coord_start = pa
                        coord_perpend = pp_i
                        coord_median = pm_i
                    if abs(angle_j - min_angle) < EPS:
                        coord_start = pb
                        coord_perpend = pp_j
                        coord_median = pm_j
                    if abs(angle_k - min_angle) < EPS:
                        coord_start = pc
                        coord_perpend = pp_k
                        coord_median = pm_k
    return ans_vertex, coord_start, coord_perpend, coord_median


class Ui(QtWidgets.QMainWindow):
    def __init__(self):
        super(Ui, self).__init__()
        uic.loadUi("./lab_01_31/template.ui", self)

        self.scene = QGraphicsScene()
        self.graphicsView.setScene(self.scene)

        self.need_grid()
        self.add_grid()
        self.greenBrush = QBrush(Qt.green)
        self.redBrush = QBrush(Qt.red)
        self.blueBrush = QBrush(Qt.blue)

        self.pen = QPen(Qt.red)

        self.add_point_button.clicked.connect(self.add_point)
        self.del_point_button.clicked.connect(self.del_point)
        self.solve_task_button.clicked.connect(self.draw_solution)

        self.about_author.triggered.connect(show_author)
        self.about_task.triggered.connect(show_task)

        self.graphicsView.mousePressEvent = self.mousePressEvent
        self.graphicsView.wheelEvent = self.wheel_event
        self.graphicsView.mouseReleaseEvent = self.mouseReleaseEvent
        self.graphicsView.mouseMoveEvent = self.mouseMoveEvent

        self.show()

    def need_grid(self):
        global max_win_size
        flag = False
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

    def add_grid(self):
        max_width = max_win_size[0]
        max_height = max_win_size[1]
        grid_interval = max_win_size[2]
        if grid_interval == 0:
            grid_interval = 20
        start_grid_width = - ((max_width // 2) + grid_interval - (max_width // 2) % grid_interval)
        start_grid_height = - ((max_height // 2) + grid_interval - (max_height // 2) % grid_interval)
        end_grid_width = (max_width // 2) - (max_width // 2) % grid_interval
        end_grid_height = (max_height // 2) - (max_width // 2) % grid_interval
        pen = QPen(Qt.darkGray)
        pen_width = 1 if int(1 / scale) == 0 else int(1 / scale)
        pen.setWidth(pen_width)
        for x in range(start_grid_width, end_grid_width, grid_interval):
            line = QGraphicsLineItem(x, start_grid_height, x, end_grid_height)
            line.setPen(pen)
            grid_lines.append(line)
            self.scene.addItem(line)
        for y in range(start_grid_height, end_grid_height, grid_interval):
            line = QGraphicsLineItem(start_grid_width, y, end_grid_width, y)
            line.setPen(pen)
            grid_lines.append(line)
            self.scene.addItem(line)

        axis_x = QGraphicsLineItem(-300 * (1 / scale), 0, 300 * (1 / scale), 0)
        axis_y = QGraphicsLineItem(0, -300 * (1 / scale), 0, 300 * (1 / scale))
        pen.setColor(Qt.white)
        grid_lines.append(axis_x)
        grid_lines.append(axis_y)
        axis_x.setPen(pen)
        axis_y.setPen(pen)
        self.scene.addItem(axis_x)
        self.scene.addItem(axis_y)

    def add_point(self):
        x_txt = self.set_x_field.text()
        y_txt = self.set_y_field.text()
        if x_txt == '' or y_txt == '':
            show_err_win("Не введены координаты точки.")
        else:
            try:
                x, y = float(x_txt), float(y_txt)
                new_point = Point(x, y)
                for point in point_list:
                    if point == new_point:
                        show_war_win("Введенная точка уже существует.")
                        break
                else:
                    point_list.append(new_point)
                    self.scroll_list.addItem(f'{len(point_list)}.({round(x, 2)}; {round(y, 2)})')
                    self.draw_point(x, -y)
                    self.clear_fields()
                    point_scale.append(1 / scale)
            except:
                show_err_win("Введены некорректные символы.")

    def add_point_by_click(self, event):
        pos = event.pos()
        scene_pos = self.graphicsView.mapToScene(pos)
        p_x, p_y = scene_pos.x(), scene_pos.y()
        point = QGraphicsEllipseItem(p_x, p_y, 5 * (1 / scale), 5 * (1 / scale))
        point_scale.append(1 / scale)
        point.setBrush(self.redBrush)
        self.scene.addItem(point)
        point_list.append(Point(p_x, -p_y))
        self.scroll_list.addItem(f'{len(point_list)}.({round(p_x, 2)}; {round(-p_y, 2)})')
        scene_point_list.append(point)

    def clear_fields(self):
        self.set_y_field.setText('')
        self.set_x_field.setText('')

    def del_point(self):
        x_txt = self.set_x_field.text()
        y_txt = self.set_y_field.text()
        if x_txt == '' or y_txt == '':
            show_err_win("Не введены координаты точки.")
        else:
            try:
                x, y = float(x_txt), float(y_txt)
                if abs(x) > 700 or abs(y) > 420:
                    show_err_win("Точка за пределами сетки")
                del_point = Point(x, y)
                for i in range(len(point_list)):
                    if point_list[i] == del_point:
                        self.scene.removeItem(scene_point_list[i])
                        point_list.pop(i)
                        scene_point_list.pop(i)
                        point_scale.pop(i)
                        self.update_scroll_list()
                        break
                self.clear_fields()
            except:
                show_err_win("Введены некорректные символы.")

    def update_scroll_list(self):
        self.scroll_list.clear()
        for i in range(len(point_list)):
            self.scroll_list.addItem(f'{i}.({round(point_list[i].x, 2)}; {round(point_list[i].y, 2)})')

    def draw_point(self, p_x, p_y):
        point = QGraphicsEllipseItem(p_x, p_y, 5 * (1 / scale), 5 * (1 / scale))
        point.setBrush(self.redBrush)
        self.scene.addItem(point)
        scene_point_list.append(point)

    def del_point_by_click(self, event):
        pos = event.pos()
        scene_pos = self.graphicsView.mapToScene(pos)
        min_diff = 100 * (1 / scale)
        del_point_id = -1
        for i in range(len(point_list)):
            if abs(scene_pos.x() - point_list[i].x) + abs(scene_pos.y() + point_list[i].y) < min_diff:
                min_diff = abs(scene_pos.x() - point_list[i].x) + abs(scene_pos.y() + point_list[i].y)
                del_point_id = i
        if min_diff > 10 * (1 / scale):
            show_err_win("Кажется, вы пытаетесь удалить несуществующую точку.\nПопробуйте кликнуть ближе к точке.")
        else:
            self.scene.removeItem(scene_point_list[del_point_id])
            point_list.pop(del_point_id)
            scene_point_list.pop(del_point_id)
            point_scale.pop(del_point_id)
            self.update_scroll_list()

    def mousePressEvent(self, event):
        global dragging, last_pos
        if event.buttons() == Qt.LeftButton:
            dragging = True
            last_pos = event.pos()
        elif event.buttons() == Qt.RightButton:
            self.del_point_by_click(event)

    def draw_solution(self):
        vertexes, coord_start, coord_perpend, coord_median = solve_task()

        side_1 = QGraphicsLineItem(vertexes[0].x, vertexes[0].y, vertexes[1].x, vertexes[1].y)
        side_2 = QGraphicsLineItem(vertexes[1].x, vertexes[1].y, vertexes[2].x, vertexes[2].y)
        side_3 = QGraphicsLineItem(vertexes[2].x, vertexes[2].y, vertexes[0].x, vertexes[0].y)
        perpend = QGraphicsLineItem(coord_start.x, coord_start.y, coord_perpend.x, coord_perpend.y)
        median = QGraphicsLineItem(coord_start.x, coord_start.y, coord_median.x, coord_median.y)

        pen_sides = QPen(Qt.magenta)
        pen_median = QPen(Qt.green)
        pen_perpend = QPen(Qt.yellow)

        pen_sides.setWidth(2)
        pen_median.setWidth(2)
        pen_perpend.setWidth(2)

        side_1.setPen(pen_sides)
        side_2.setPen(pen_sides)
        side_3.setPen(pen_sides)
        perpend.setPen(pen_perpend)
        median.setPen(pen_median)

        self.scene.addItem(side_1)
        self.scene.addItem(side_2)
        self.scene.addItem(side_3)
        self.scene.addItem(perpend)
        self.scene.addItem(median)

    def wheel_event(self, event):
        global scale
        factor = 1.2

        if event.angleDelta().y() > 0:
            self.graphicsView.scale(factor, factor)
        else:
            self.graphicsView.scale(1.0 / factor, 1.0 / factor)

        scale = self.graphicsView.transform().m11()  # Получаем текущий масштаб по оси X (и Y)
        for i in range(len(scene_point_list)):
            point = scene_point_list[i]
            point.setTransformOriginPoint(point.boundingRect().center())
            point.setScale(1 / (scale * point_scale[i]))
        if self.need_grid():
            for grid_line in grid_lines:
                self.scene.removeItem(grid_line)
            self.add_grid()

    def mouseReleaseEvent(self, event: QMouseEvent):
        global dragging
        if event.button() == Qt.LeftButton:
            dragging = False
            self.add_point_by_click(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        global last_pos
        if dragging:
            dx = event.pos().x() - last_pos.x()
            dy = event.pos().y() - last_pos.y()
            self.graphicsView.horizontalScrollBar().setValue(self.graphicsView.horizontalScrollBar().value() - dx)
            self.graphicsView.verticalScrollBar().setValue(self.graphicsView.verticalScrollBar().value() - dy)
            last_pos = event.pos()
            if self.need_grid():
                for grid_line in grid_lines:
                    self.scene.removeItem(grid_line)
                self.add_grid()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Ui()
    app.exec_()
