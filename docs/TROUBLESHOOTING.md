# Troubleshooting

## Port Conflicts
If `dev.ps1` fails with an `[Errno 98] Address already in use` error:
- Ensure no other FastAPI services are running on ports `8000` or `8001`.
- Run `netstat -ano | findstr :8000` to find the PID, then `taskkill /PID <id> /F`.

## Python ModuleNotFoundError
If you see `No module named 'packages'`:
- The backend scripts rely on `PYTHONPATH`. Our `test.ps1` script handles this automatically, but if you run tests manually, ensure you set `$env:PYTHONPATH = "./backend;./realtime-agent"`.

## VAD ONNX Errors
If Silero VAD crashes on boot:
- Ensure you have the Microsoft Visual C++ Redistributable installed, which ONNX Runtime requires on Windows.
