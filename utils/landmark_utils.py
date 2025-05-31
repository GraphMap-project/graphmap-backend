import logging
import random

import networkx as nx
import osmnx as ox

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def get_regional_center_nodes(G, city_names):
    """Функция для кодирования региональных центров в координаты"""
    center_nodes = []
    for city in city_names:
        try:
            # Получаем координаты по названию города
            lat, lon = ox.geocode(city)
            # Ищем ближайший узел графа
            node = ox.distance.nearest_nodes(G, X=lon, Y=lat)
            center_nodes.append(node)
        except Exception as e:
            logger.exception(f"Error processing this city {city}: {e}")
    return center_nodes


def select_global_landmarks(G, regional_centers, k=5):
    """
    Выбирает k ориентиров (landmarks) из списка региональных центров с помощью эвристики
    "самые удалённые узлы".

    Первый узел выбирается случайно, а каждый последующий — тот, который наиболее удалён
    от уже выбранных.

    Parameters:
        G: граф NetworkX (должен быть взвешенным по расстоянию — атрибут 'length')
        regional_centers: список узлов-городов, из которых выбираются ориентиры
        k: количество ориентиров, которые нужно выбрать (по умолчанию 5)

    Returns:
        landmarks: список выбранных узлов (landmarks)
    """
    # Проверка: нельзя выбрать больше ориентиров, чем есть региональных центров
    if k > len(regional_centers):
        raise ValueError("k cannot be greater than the number of regional centers.")

    # Случайный выбор первого ориентира из списка региональных центров
    first = random.choice(regional_centers)
    landmarks = [first]

    # Повторяем k-1 раз, чтобы выбрать ещё (k-1) ориентиров
    for _ in range(k - 1):
        dists = {}  # сюда сохраняем расстояния от каждого кандидата до ближайшего из уже выбранных landmarks
        for n in regional_centers:
            if n in landmarks:
                continue  # пропускаем уже выбранные ориентиры

            min_dist = float(
                "inf"
            )  # минимальное расстояние до любого из текущих landmarks
            for l in landmarks:
                # Проверяем, существует ли путь от текущего landmarks до n
                if nx.has_path(G, l, n):
                    try:
                        # Находим длину кратчайшего пути от l до n
                        length = nx.shortest_path_length(G, l, n, weight="length")
                        if length < min_dist:
                            min_dist = length
                    except nx.NetworkXNoPath:
                        continue  # если пути нет — пропускаем
            # Сохраняем расстояние, если оно успешно найдено
            if min_dist != float("inf"):
                dists[n] = min_dist
        # Если не удалось найти ни одного достижимого центра — выходим
        if not dists:
            logger.exception(
                "No reachable regional centers found for the remaining landmarks."
            )
            break

        # Выбираем тот узел, который дальше всего от ближайшего из текущих landmarks
        farthest = max(dists.items(), key=lambda x: x[1])[0]
        landmarks.append(farthest)

    return landmarks


def preprocess_landmarks_distances(G, landmarks):
    """
    Функция для предподсчета расстояний от опорных точек до всех остальных точек графа
    """
    distances = {}
    for i, node in enumerate(landmarks):
        distances[node] = nx.single_source_dijkstra_path_length(
            G, node, weight="length"
        )
    return distances
