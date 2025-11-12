import os
import sys

def main():
    app_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, app_dir)
    
    print("Available Python files:")
    for file in os.listdir(app_dir):
        if file.endswith('.py') and file != 'launcher.py':
            print(f"  - {file}")
    
    # Try importing different possible main modules
    try:
        # Try streamlit_app first (most common)
        from streamlit_app import main as app_main
        print("Starting Streamlit app...")
        app_main()
    except ImportError:
        try:
            # Try fastapi_server
            from fastapi_server import main as app_main
            print("Starting FastAPI server...")
            app_main()
        except ImportError:
            try:
                # Try agent
                from agent import main as app_main
                print("Starting agent...")
                app_main()
            except ImportError:
                try:
                    # Try adaptive_media_api
                    from adaptive_media_api import main as app_main
                    print("Starting adaptive media API...")
                    app_main()
                except ImportError:
                    try:
                        # Try banner_mcp_server
                        from banner_mcp_server import main as app_main
                        print("Starting banner MCP server...")
                        app_main()
                    except ImportError:
                        try:
                            # Try video_mcp_server
                            from video_mcp_server import main as app_main
                            print("Starting video MCP server...")
                            app_main()
                        except ImportError as e:
                            print(f'Error: No main module found!')
                            print('Available Python files:')
                            for file in os.listdir(app_dir):
                                if file.endswith('.py') and file != 'launcher.py':
                                    print(f'  {file}')
                            input('Press Enter to exit...')
    except Exception as e:
        print(f'Application error: {e}')
        import traceback
        traceback.print_exc()
        input('Press Enter to exit...')

if __name__ == '__main__':
    main()