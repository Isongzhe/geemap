import solara
import src.state as state

# Import Pages
from src.step1.app import Page as Step1Page
from src.step2.app import Page as Step2Page

@solara.component
def Page():
    current = state.current_step.value
    
    with solara.Column(style={"height": "100vh"}):
        if current == 1:
            Step1Page()
        elif current == 2:
            Step2Page()
        else:
            solara.Error(f"Unknown Step: {current}")

if __name__ == "__main__":
    Page()
