import asyncio
import csv

import aiohttp
from sqlalchemy import delete, insert
from sqlalchemy.orm import Session

from models import Building, Room

BASE_URL = "https://m.blog.naver.com/api/blogs/hyerica4473/search/post"
search_keyword = "%EA%B1%B4%EB%AC%BC%20%EB%82%B4%EB%B6%80%20%EA%B5%AC%EC%A1%B0%EB%8F%84"


async def parse_building_location() -> dict[str, list[str]]:
    building_list = {}
    with open("resources/location.csv", "r", encoding="utf-8") as file:
        reader = csv.reader(file)
        for name, latitude, longitude in reader:
            building_list[name] = [latitude, longitude]
    return building_list


async def fetch_building_list(buildings: list[dict]) -> list[dict]:
    pages = [1, 2, 3, 4]
    urls = [f"{BASE_URL}?query={search_keyword}&page={page}" for page in pages]
    header = {"Referer": "https://m.blog.naver.com/PostSearchList.naver?blogId=hyerica4473&orderType=sim&searchText="}
    async with aiohttp.ClientSession(headers=header) as session:
        tasks = []
        for url in urls:
            tasks.append(asyncio.create_task(fetch_building_page(session, url)))
        values = await asyncio.gather(*tasks)
    building_list = []
    for value in values:
        building_list.extend(filter(lambda x: "건물 내부 구조도" in x.get("title"), value))

    location_list = await parse_building_location()
    for building in building_list:
        title = str(building.get("title"))\
            .replace("[자료실] ", "")\
            .replace('<em class="highlight">건물 내부 구조도</em>', "").strip()
        post_no = building.get("logNo")
        if len(list(filter(lambda x: title == x.get("name"), buildings))) > 0:
            item = next(filter(lambda x: title == x.get("name"), buildings))
            item["link"] = f"https://m.blog.naver.com/hyerica4473/{post_no}"
            if location_list.get(title):
                item["latitude"] = location_list.get(title)[0]
                item["longitude"] = location_list.get(title)[1]
        else:
            item = {"name": title, "link": f"https://m.blog.naver.com/hyerica4473/{post_no}"}
            if location_list.get(title):
                item["latitude"] = location_list.get(title)[0]
                item["longitude"] = location_list.get(title)[1]
            buildings.append(item)
    for building in buildings:
        if building.get("latitude") is None or building.get("longitude") is None:
            building["latitude"] = location_list.get(building.get("name"))[0]
            building["longitude"] = location_list.get(building.get("name"))[1]
    return buildings


async def fetch_building_page(session, url) -> list[dict]:
    async with session.get(url) as response:
        response_json = await response.json()
        return response_json.get("result").get("list")


async def insert_building(db_session: Session, data: list[dict]):
    delete_statement = delete(Room)
    db_session.execute(delete_statement)
    delete_statement = delete(Building)
    db_session.execute(delete_statement)
    db_session.execute(
        insert(Building),
        list(map(lambda x: {
            "building_id": x.get("id"),
            "name": x.get("name"),
            "campus_id": 2,
            "latitude": x.get("latitude"),
            "longitude": x.get("longitude"),
            "link": x.get("link")
        }, data))
    )
    db_session.commit()
