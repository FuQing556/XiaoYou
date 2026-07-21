"""WebSocket end-to-end test"""
import asyncio
import json
import sys
sys.path.insert(0, '.')
import websockets

async def test():
    # Connect
    ws = await websockets.connect('ws://127.0.0.1:8765/ws')
    print('[1] Connected')

    # Receive initial messages (emotion, mode, greeting)
    for i in range(5):
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
            data = json.loads(msg)
            t = data.get('type','?')
            txt = data.get('text','')[:40] if data.get('text') else ''
            print(f'  recv[{i}]: type={t} text={txt}')
        except asyncio.TimeoutError:
            print(f'  recv[{i}]: (timeout)')
            break

    # Send chat message
    print('[2] Sending chat...')
    await ws.send(json.dumps({"type":"chat","content":"你好小悠！"}))

    # Receive response
    for i in range(10):
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=15.0)
            data = json.loads(msg)
            t = data.get('type','?')
            print(f'  reply[{i}]: type={t}', end='')
            if t == 'perform':
                print(f' text={data.get("text","")[:50]} expr={data.get("expression")} actions={data.get("actions")} audio={"YES" if data.get("audio_url") else "NO"}')
            elif t == 'thinking':
                print(f' state={data.get("state")}')
            elif t == 'cancel':
                print('')
            else:
                print(f' data={str(data)[:80]}')
            if t == 'perform':
                print('[OK] End-to-end test PASSED')
                break
        except asyncio.TimeoutError:
            print(f'  reply[{i}]: (timeout)')
            break

    await ws.close()
    print('[3] Done')

if __name__ == '__main__':
    asyncio.run(test())
