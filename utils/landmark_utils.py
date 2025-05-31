import random

import networkx as nx
import osmnx as ox


def get_regional_center_nodes(G, city_names):
    center_nodes = []
    for city in city_names:
        try:
            # Получаем координаты по названию города
            lat, lon = ox.geocode(city)
            # Ищем ближайший узел графа
            node = ox.distance.nearest_nodes(G, X=lon, Y=lat)
            center_nodes.append(node)
        except Exception as e:
            print(f"Error processing this city {city}: {e}")
    return center_nodes


def select_global_landmarks(G, regional_centers, k=5):
    """
    Selects k landmarks from regional_centers using the farthest-node heuristic.
    The first is random, others are the farthest from already chosen.
    """
    if k > len(regional_centers):
        raise ValueError("k cannot be greater than the number of regional centers.")

    # Start with a random regional center
    first = random.choice(regional_centers)
    landmarks = [first]

    for _ in range(k - 1):
        dists = {}
        for n in regional_centers:
            if n in landmarks:
                continue
            min_dist = float("inf")
            for l in landmarks:
                if nx.has_path(G, l, n):
                    try:
                        length = nx.shortest_path_length(G, l, n, weight="length")
                        if length < min_dist:
                            min_dist = length
                    except nx.NetworkXNoPath:
                        continue
            if min_dist != float("inf"):
                dists[n] = min_dist

        if not dists:
            print("No reachable regional centers found for the remaining landmarks.")
            break

        farthest = max(dists.items(), key=lambda x: x[1])[0]
        landmarks.append(farthest)

    return landmarks


def preprocess_landmarks_distances(G, landmarks):
    distances = {}
    for i, node in enumerate(landmarks):
        distances[node] = nx.single_source_dijkstra_path_length(
            G, node, weight="length"
        )
    return distances
