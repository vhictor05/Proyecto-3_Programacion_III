import folium

def create_base_map(center_lat=-38.7359, center_lon=-72.5904, zoom_start=13):
    """
    Crea y retorna un mapa base centrado en Temuco o en las coordenadas indicadas.
    """
    my_map = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom_start,
        control_scale=True
    )
    return my_map
