# -*- coding: utf-8 -*-
"""Codigos de provincia del INE usados por el Portal de Subastas del BOE (dato[8])."""

PROVINCIAS = {
    "01": "Araba/Alava", "02": "Albacete", "03": "Alicante/Alacant", "04": "Almeria",
    "05": "Avila", "06": "Badajoz", "07": "Illes Balears", "08": "Barcelona",
    "09": "Burgos", "10": "Caceres", "11": "Cadiz", "12": "Castellon/Castello",
    "13": "Ciudad Real", "14": "Cordoba", "15": "A Coruna", "16": "Cuenca",
    "17": "Girona", "18": "Granada", "19": "Guadalajara", "20": "Gipuzkoa",
    "21": "Huelva", "22": "Huesca", "23": "Jaen", "24": "Leon", "25": "Lleida",
    "26": "La Rioja", "27": "Lugo", "28": "Madrid", "29": "Malaga", "30": "Murcia",
    "31": "Navarra", "32": "Ourense", "33": "Asturias", "34": "Palencia",
    "35": "Las Palmas", "36": "Pontevedra", "37": "Salamanca",
    "38": "Santa Cruz de Tenerife", "39": "Cantabria", "40": "Segovia",
    "41": "Sevilla", "42": "Soria", "43": "Tarragona", "44": "Teruel",
    "45": "Toledo", "46": "Valencia/Valencia", "47": "Valladolid", "48": "Bizkaia",
    "49": "Zamora", "50": "Zaragoza", "51": "Ceuta", "52": "Melilla",
}

# Provincias con costa (para el filtro "a menos de 500 m del mar").
COSTERAS = [
    "03", "04", "07", "08", "11", "12", "15", "17", "18", "20", "21",
    "27", "29", "30", "33", "35", "36", "38", "39", "43", "46",
    "48", "51", "52",
]

def nombre(cod):
    return PROVINCIAS.get(cod, cod)
