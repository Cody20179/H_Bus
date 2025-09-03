from fastapi import FastAPI
import uvicorn

app = FastAPI(title="小巴")

@app.post("/Buson")
def Bus_on():
    return "ABC-0123,2014/10/10 10:10:10,0,0,A,121.374193,25.000137,13.2,120.0,20,5,12345678,\r"

if __name__ == "__main__":
    uvicorn.run("Realtime_Bus:app", host="0.0.0.0", port=8501, reload=True)