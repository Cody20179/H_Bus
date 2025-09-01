from fastapi import FastAPI, HTTPException, Query, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel
import requests, uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Stop(BaseModel):
    name: str
    time: Optional[str] = None
    note: Optional[str] = ""

class BusRouteDetail(BaseModel):
    id: str
    name: str
    from_: str
    to: str
    next_bus_time: str
    eta: int
    stops: List[Stop]
    current_index: int
    direction: int   # 0=去程 1=回程

class RouteSimple(BaseModel):
    id: str
    name: str
    from_: str
    to: str
    desc: str

class BusRouteDetail(BaseModel):
    id: str
    name: str
    from_: str
    to: str
    next_bus_time: str
    eta: int
    stops: List[Stop]
    current_index: int

class RouteSimple(BaseModel):
    id: str
    name: str
    from_: str
    to: str
    info: Optional[str] = None  # 可附加資訊

ROUTE_RAW = {
    "5": {
        "name": "市民小巴5(洽公直達線)",
        "from_": "花蓮轉運站",
        "to": "花蓮縣政府-正門",
        "desc": "洽公直達路線",
        "stops": [
            "花蓮轉運站", "花蓮縣動防所", "花蓮縣稅務局", "花蓮縣政府-後門",
            "花蓮地方法院", "婦幼親創園區", "花蓮縣衛生局", "花蓮縣政府-正門"
        ]
    },
    "6": {
        "name": "市民小巴6(醫療照護線)",
        "from_": "花蓮轉運站",
        "to": "門諾醫院",
        "desc": "醫療照護專線",
        "stops": [
            "花蓮轉運站", "市民廣場", "明禮國小", "花蓮醫院(慈愛大樓)",
            "璽濱飯店", "煙波飯店", "中美民權八街", "門諾醫院"
        ]
    },
    "7": {
        "name": "市民小巴7(市區夜環線)-單向循環線",
        "from_": "花蓮轉運站",
        "to": "花蓮轉運站",
        "desc": "夜間市區單向環線",
        "stops": [
            "花蓮轉運站", "勤天商旅", "市立圖書館", "麗星飯店",
            "花蓮又一村文創園區", "花蓮文創園區", "日出香榭大道1", "日出香榭大道2",
            "東大門夜市", "中華路", "將軍府商圈", "勤天商旅", "花蓮轉運站"
        ]
    },
    "8": {
        "name": "市民小巴8(行動遊花蓮)",
        "from_": "花蓮轉運站",
        "to": "七星柴魚博物館",
        "desc": "花蓮觀光遊園",
        "stops": [
            "花蓮轉運站","將軍府","松園別館","菁華林苑-花蓮港山林事業所","花蓮文化中心石雕公園",
            "花蓮港景觀橋","花蓮觀光漁港","四八高地","花蓮酒廠","花蓮文化創意產業園區","花蓮又一村文創園區",
            "張家樹園","吉安好客藝術村","吉安慶修院","南埔公園","知卡宣綠森林親水公園","南華林業園區",
            "佐倉步道","北埔車站","吉安車站","北濱公園","美崙山公園","後山‧山後故事館","七星柴魚博物館"
        ]
    },
}

BUS_DETAIL_RAW = {
    "5": {  # ...你的原本5號（去回都有，保留）
        "name": "市民小巴5(洽公直達線)",
        "from_": "花蓮轉運站",
        "to": "花蓮縣政府 正門",
        "directions": [
            {  # direction 0: 去程
                "stops": [
                    {"name": "花蓮轉運站", "time": "11:20", "note": "首站"},
                    {"name": "花蓮縣動防所", "time": "11:23"},
                    {"name": "花蓮縣稅務局", "time": "11:26"},
                    {"name": "花蓮縣政府 後門", "time": "11:29"},
                    {"name": "花蓮地方法院", "time": "11:32"},
                    {"name": "婦幼親創園區", "time": "11:36"},
                    {"name": "花蓮縣衛生局", "time": "11:41"},
                    {"name": "花蓮縣政府 正門", "time": "11:45", "note": "末站"},
                ],
                "next_bus_time": "11:20",
                "eta": 5,
                "current_index": 3,
            },
            {  # direction 1: 回程
                "stops": [
                    {"name": "花蓮縣政府 正門", "time": "12:00", "note": "首站"},
                    {"name": "花蓮縣衛生局", "time": "12:03"},
                    {"name": "婦幼親創園區", "time": "12:07"},
                    {"name": "花蓮地方法院", "time": "12:11"},
                    {"name": "花蓮縣政府 後門", "time": "12:15"},
                    {"name": "花蓮縣稅務局", "time": "12:18"},
                    {"name": "花蓮縣動防所", "time": "12:21"},
                    {"name": "花蓮轉運站", "time": "12:25", "note": "末站"},
                ],
                "next_bus_time": "12:00",
                "eta": 6,
                "current_index": 1,
            },
        ],
    },
    "6": {  # ...你的原本6號（去回都有，保留）
        "name": "市民小巴6(醫療照護線)",
        "from_": "花蓮轉運站",
        "to": "門諾醫院",
        "directions": [
            {  # direction 0: 去程
                "stops": [
                    {"name": "花蓮轉運站", "time": "10:00", "note": "首站"},
                    {"name": "市民廣場", "time": "10:03"},
                    {"name": "明禮國小", "time": "10:07"},
                    {"name": "花蓮醫院(慈愛大樓)", "time": "10:11"},
                    {"name": "璽濱飯店", "time": "10:15"},
                    {"name": "煙波飯店", "time": "10:19"},
                    {"name": "中美民權八街", "time": "10:23"},
                    {"name": "門諾醫院", "time": "10:27", "note": "末站"},
                ],
                "next_bus_time": "10:00",
                "eta": 5,
                "current_index": 3,
            },
            {  # direction 1: 回程
                "stops": [
                    {"name": "門諾醫院", "time": "10:40", "note": "首站"},
                    {"name": "中美民權八街", "time": "10:44"},
                    {"name": "煙波飯店", "time": "10:48"},
                    {"name": "璽濱飯店", "time": "10:52"},
                    {"name": "花蓮醫院(慈愛大樓)", "time": "10:56"},
                    {"name": "明禮國小", "time": "11:00"},
                    {"name": "市民廣場", "time": "11:04"},
                    {"name": "花蓮轉運站", "time": "11:08", "note": "末站"},
                ],
                "next_bus_time": "10:40",
                "eta": 5,
                "current_index": 2,
            },
        ]
    },
    "7": {  # 單向循環，**只保留一組 direction**
        "name": "市民小巴7(市區夜環線)-單向循環線",
        "from_": "花蓮轉運站",
        "to": "花蓮轉運站",
        "directions": [
            {
                "stops": [
                    {"name": "花蓮轉運站", "time": "18:00", "note": "首站"},
                    {"name": "市立圖書館", "time": "18:03"},
                    {"name": "麗星飯店", "time": "18:07"},
                    {"name": "花蓮又一村文創園區", "time": "18:10"},
                    {"name": "花蓮文創園區", "time": "18:14"},
                    {"name": "日出香榭大道1", "time": "18:18"},
                    {"name": "日出香榭大道2", "time": "18:22"},
                    {"name": "東大門夜市", "time": "18:25"},
                    {"name": "中華路", "time": "18:29"},
                    {"name": "將軍府商圈", "time": "18:33"},
                    {"name": "花蓮轉運站", "time": "18:38", "note": "末站"},
                ],
                "next_bus_time": "18:00",
                "eta": 7,
                "current_index": 6,
            },
        ]
    },
    "8": {  # 單向觀光，**只保留一組 direction**
        "name": "市民小巴8(行動遊花蓮)",
        "from_": "花蓮轉運站",
        "to": "七星柴魚博物館",
        "directions": [
            {
                "stops": [
                    {"name": "花蓮轉運站"},
                    {"name": "將軍府"},
                    {"name": "松園別館"},
                    {"name": "菁華林苑-花蓮港山林事業所"},
                    {"name": "花蓮文化中心石雕公園"},
                    {"name": "花蓮港景觀橋"},
                    {"name": "花蓮觀光漁港"},
                    {"name": "四八高地"},
                    {"name": "臺灣菸酒股份有限公司-花蓮酒廠"},
                    {"name": "花蓮文化創意產業園區"},
                    {"name": "花蓮又一村文創園區"},
                    {"name": "張家樹園"},
                    {"name": "吉安好客藝術村"},
                    {"name": "吉安慶修院"},
                    {"name": "南埔公園"},
                    {"name": "知卡宣綠森林親水公園"},
                    {"name": "南華林業園區"},
                    {"name": "佐倉步道"},
                    {"name": "北埔車站"},
                    {"name": "吉安車站"},
                    {"name": "北濱公園"},
                    {"name": "美崙山公園"},
                    {"name": "後山‧山後故事館"},
                    {"name": "七星柴魚博物館"},
                ],
                "next_bus_time": "09:00",
                "eta": 10,
                "current_index": 5,
            },
        ]
    },
}

def api_login():
    data = {
        "username": "admin",
        "password": "8nc2>dRC3f"
    }
    try:
        resp = requests.post("http://192.168.0.126:8001/auth/login", json=data, timeout=5)
        return resp.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


def Got_all_road():
    api_login()
    try:
        resp = requests.get("http://192.168.0.126:8001/routes/description", timeout=5)
        print(resp)
        return resp.json()
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_route_stations(route):
    api_login()  # 先登入
    url = f"http://192.168.0.126:8001/routes/{route}/stations/0"
    try:
        resp = requests.get(url, timeout=5)
        data = resp.json()
        if "stations" not in data:
            raise Exception("資料格式錯誤")
        return data["stations"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得站點失敗: {e}")
    
def get_route_name_by_id(route_id):
    result = Got_all_road()
    if not result or 'routes' not in result:
        return None
    for r in result['routes']:
        if r['route_id'] == route_id:
            return r['route']
    return None

@app.get("/api/bus/routes", response_model=List[RouteSimple])
def list_routes():
    result = Got_all_road()
    if not result or 'routes' not in result:
        raise HTTPException(status_code=500, detail="取得路線失敗")
    routes = []
    for r in result['routes'][:2]:   # 只取前兩條
        desc = r['description']
        parts = desc.split(" ", 1)
        if len(parts) == 2:
            name, path = parts
            if '-' in path:
                from_, to = path.split('-', 1)
            else:
                from_, to = path, ''
        else:
            name = desc
            from_, to = '', ''
        routes.append(RouteSimple(
            id=r['route'],
            name=name,
            from_=from_.strip(),
            to=to.strip(),
            desc=desc.strip(),
        ))
    return routes

@app.get("/api/bus/routes/all", response_model=List[RouteSimple])
def list_all_routes():
    result = Got_all_road()
    print(result)
    if not result or 'routes' not in result:
        raise HTTPException(status_code=500, detail="取得路線失敗")
    routes = []
    for r in result['routes']:
        desc = r['description']
        parts = desc.split(" ", 1)
        if len(parts) == 2:
            name, path = parts
            if '-' in path:
                from_, to = path.split('-', 1)
            else:
                from_, to = path, ''
        else:
            name = desc
            from_, to = '', ''
        routes.append(RouteSimple(
            id=r['route'],           # <--- 用 route（如 "five_direct_bus_line_outbound"）
            name=name,
            from_=from_.strip(),
            to=to.strip(),
            desc=desc.strip(),
        ))
    return routes


@app.get("/api/bus/detail/{route}")
def bus_route_detail(route: str, direction: int = 0):
    print(route, direction)
    stations = get_route_stations(route)
    print(stations)
    if not stations:
        raise HTTPException(status_code=404, detail="查無站點")
    return {"stations": stations, "route": route}

@app.post("/api/auth/register")
async def register(data: dict):
    # 做帳號註冊流程...
    return {"success": True}

if __name__ == "__main__":
    uvicorn.run("Bus:app", host="0.0.0.0", port=8000, reload=True)