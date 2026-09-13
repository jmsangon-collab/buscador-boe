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

# Comunidad Autonoma de cada provincia (por codigo INE).
CCAA_PROVINCIAS = {
    "Andalucia": ["04", "11", "14", "18", "21", "23", "29", "41"],
    "Aragon": ["22", "44", "50"],
    "Asturias": ["33"],
    "Illes Balears": ["07"],
    "Canarias": ["35", "38"],
    "Cantabria": ["39"],
    "Castilla y Leon": ["05", "09", "24", "34", "37", "40", "42", "47", "49"],
    "Castilla-La Mancha": ["02", "13", "16", "19", "45"],
    "Cataluna": ["08", "17", "25", "43"],
    "Comunitat Valenciana": ["03", "12", "46"],
    "Extremadura": ["06", "10"],
    "Galicia": ["15", "27", "32", "36"],
    "Madrid": ["28"],
    "Murcia": ["30"],
    "Navarra": ["31"],
    "Pais Vasco": ["01", "20", "48"],
    "La Rioja": ["26"],
    "Ceuta": ["51"],
    "Melilla": ["52"],
}
# Indice inverso: codigo de provincia -> nombre de CCAA.
CCAA_DE = {cod: ccaa for ccaa, cods in CCAA_PROVINCIAS.items() for cod in cods}


def nombre(cod):
    return PROVINCIAS.get(cod, cod)


def ccaa(cod):
    return CCAA_DE.get(cod)
