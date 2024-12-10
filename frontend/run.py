from interface import create_interface

if __name__ == "__main__":
    interface = create_interface()
    interface.launch(
        server_name="0.0.0.0",
        server_port=7861,
        share=False,
        inbrowser=True
    )
