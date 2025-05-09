from typing import List, Union

from class_point import Point


def get_new_coords(matrix: List[List[Union[float, int]]], points: List[Point]) -> List[List[Union[float, int]]]:
    for _ in range(len(points)):
        points[_] = mul_matrices(matrix, points[_])
    return points


def mul_matrices(matrix: List[List[Union[float, int]]], point: Point) -> Point:
    point_matrix = (point.x, point.y, 1)
    result = [0] * 3
    for i in range(len(matrix)):
        for k in range(len(point_matrix)):
            result[i] += matrix[i][k] * point_matrix[k]
    result.pop()
    return Point(*result)
