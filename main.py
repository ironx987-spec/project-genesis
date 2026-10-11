# main.py
# Точка входа для запуска ассистента DOOM
import sys

def main():
    print("=== STARTING DOOM ASSISTANT SYSTEM ===")
    try:
        import main_agent
        main_agent.start()
    except ImportError:
        print("[DOOM ERROR] main_agent.py not found or failed to load.")
    except Exception as e:
        print(f"[DOOM ERROR] System crash: {e}")

if __name__ == "__main__":
    main()
