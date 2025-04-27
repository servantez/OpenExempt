import json
import gradio as gr
from open_exempt import generate_demo
from source.config import Config
from source.task_id import TaskID
from source.jurisdiction import Jurisdiction


'''
OpenExempt Demo Application
This module creates a Gradio web interface to be hosted on Huggingface Spaces.
The interface allows users to easily choose configuration settings, which are used to dynamically construct tasks and solutions.
'''

# Load default config
config = Config("demo")

def process_demo_request(start_task, terminal_task, asset_count_min, asset_count_max, married_percentage, domicile_count_min, domicile_count_max, state_jurisdictions, dataset_size, irrelevant_facts, opinions):
    config.start_task_id = TaskID.display_name_to_task_id(start_task).value
    config.terminal_task_id = TaskID.display_name_to_task_id(terminal_task).value
    config.asset_count_min = asset_count_min
    config.asset_count_max = asset_count_max
    config.married_percentage = married_percentage / 100
    config.domicile_count_min = domicile_count_min
    config.domicile_count_max = domicile_count_max
    config.state_jurisdictions = state_jurisdictions
    config.irrelevant_asset_facts = 'Irrelevant Asset Facts' in irrelevant_facts
    config.irrelevant_domicile_facts = 'Irrelevant Domicile Facts' in irrelevant_facts
    config.asset_opinions = 'Asset Opinions' in opinions
    config.domicile_opinions = 'Domicile Opinions' in opinions

    case, task = generate_demo(config)
    prompt = task.prompt()
    solution = task.solution
    # Solution can either be a string or dictionary. Solution will be displayed in a JSON output component, so if it is a string, wrap it.
    if isinstance(solution, str):
        solution = {"solution": solution}

    return prompt, solution, case.to_dict()

# Custom CSS for layout enhancements
custom_css = """
    .gray-bg { background-color: #e5e5e5 !important; padding: 20px; border-radius: 10px; }
    .header-text { font-size: 26px; font-weight: 600; margin-bottom: 10px; }
"""

with gr.Blocks(css=custom_css) as demo:
    # Introductory Section
    gr.Markdown("# 🧾 OpenExempt: a Diagnostic Benchmark for Legal Reasoning", elem_classes="header-text")
    gr.Markdown("OpenExempt is a dynamic legal reasoning benchmark which gives users control over crafting legal scenarios through a set of configuration options. This interface is a demo to illustrate the benchmark's ability to construct tasks and solutions on demand.")
    gr.Markdown("*Use the tabs below to set configuration options based on your preferences.*")


    with gr.Tabs():
        with gr.Tab("📘 About the Benchmark"):
            with gr.Row():
                with gr.Column():
                    gr.Markdown("## Benchmark Overview")
                    gr.Markdown(" OpenExempt is named for its central task, exempting assets under the United States Bankruptcy Code. A person filing for bankruptcy, called the Debtor, is allowed to protect certain property from seizure by creditors. An exemption defines a category of property which can be protected - for example, up to $4,450 in a motor vehicle. Each state defines its own exemption statutes which differ considerably in regards to which assets are protected. The debtor may claim state or federal exemptions, unless their state specifically prohibits the use of federal exemptions, known as \"opt-out\". Which state exemption laws apply to a given case is determined by where the debtor lived prior to filing.")
                with gr.Column():
                    gr.Image(value="OE_exemption.png", elem_classes="gray-bg", show_label=False, height=340, width=460)

        with gr.Tab("📋 Task Scope"):
            gr.Markdown("## Defining the Scope")
            with gr.Row():
                with gr.Column():
                    gr.Markdown("The process of exempting assets involves a sequence of subtasks - each requiring different types of reasoning. OpenExempt enables users to evaluate the entire exemption process, a single subtask, or any sequential interval of subtasks to examine specific combinations of reasoning skills.")
                    gr.Markdown("## Subtasks")
                    gr.Markdown("*Select governing exemption laws.* To determine which state exemptions a debtor is allowed to claim, the Bankruptcy code considers which states the debtor has lived in the preceding 730 days. This task requires identifying the governing jurisdiction given residency dates and locations.")
                    gr.Markdown("*Asset Exemption (categorization).* This task involves identifying applicable exemptions for each asset based on the governing state exemption laws. This is a multi-label classification problem since multiple exemptions can apply to a single asset. Federal exemptions may also need to be considered depending on whether the corresponding state has opted-out.")
                    gr.Markdown("*Asset exemption (dollar value).* For the selected state exemptions, and federal exemptions if applicable, determine how much of the fair market value of each asset is protected.")
                    gr.Markdown("*Identify non-exempt assets.* Based on the optimal exemptions that can be claimed, determine the total dollar value of assets not protected under the exemption laws of each applicable jurisdiction.")
                    gr.Markdown("*Select optimal exemptions.* Select the optimal exemption set by minimizing the dollar value of non-exempt assets.")
                with gr.Column():
                    gr.Image(value="OE_tasks.png", show_label=False)

            with gr.Row():
                with gr.Column():
                    start_task = gr.Radio(choices=TaskID.supported_tasks() , value=TaskID.GOVERNING_JURISDICTIONS.display_name(), label="Start Task", info="The first subtask to evaluate")
                with gr.Column():
                    terminal_task = gr.Radio(choices=TaskID.supported_tasks() , value=TaskID.OPTIMAL_EXEMPTIONS.display_name(), label="End Task", info="The last subtask to evaluate (must be greater than or equal to start task)")

        with gr.Tab("🏛️ Jurisdictions & Counts"):
            state_jurisdictions = gr.CheckboxGroup(choices=Jurisdiction.supported_jurisdictions(), value=config.state_jurisdictions, label="State Jurisdictions", info="Choose which state jurisdictions will be involved (must select at least one)")
            with gr.Row():
                with gr.Column():
                    married_percentage = gr.Slider(value=config.married_percentage * 100, label="Percentage of married cases", minimum=0, maximum=100, step=10)
                    domicile_count_min = gr.Number(value=config.domicile_count_min, label="Min Residences", info='(Min: 1, Max: 5)', minimum=1, maximum=5)
                    domicile_count_max = gr.Number(value=config.domicile_count_max, label="Max Residences", info='(Must be greater than or equal to Min Residences, Max: 5)', minimum=1, maximum=5)
                with gr.Column():
                    asset_count_min = gr.Number(value=config.asset_count_min, label="Min Assets", info='(Min: 1, Max: 8)', minimum=1, maximum=8)
                    asset_count_max = gr.Number(value=config.asset_count_max, label="Max Assets", info='(Must be greater than or equal to Min Assets, Max: 8)', minimum=1, maximum=8)
                    dataset_size = gr.Number(value=1, label="Dataset Size", info='(abridged to one example for demo)', minimum=1)

        with gr.Tab("🧪 Obfuscation Settings"):
            with gr.Row():
                with gr.Column():
                    irrelevant_facts = gr.CheckboxGroup(choices=["Irrelevant Asset Facts", "Irrelevant Domicile Facts"], value=[], label="Irrelevant Facts", info="Add irrelevant facts to evaluate robustness of reasoning")
                with gr.Column():
                    opinions = gr.CheckboxGroup(choices=["Asset Opinions", "Domicile Opinions"], value=[], label="Opinion Statements", info="Add opinions to evaluate sycophancy")

    submit_btn = gr.Button("Generate Task", variant="primary")
    success_note = gr.Markdown(visible=False)
    prompt_output = gr.Textbox(label="Task Prompt", interactive=False, elem_id="prompt-box")
    solution_output = gr.JSON(label="Expected Solution")
    case_output = gr.Accordion("View Full Case JSON", open=False)
    with case_output:
        case_json = gr.JSON()

    gr.Markdown("Build notes: this demo is still in alpha. Please report any issues observed.")

    gr.HTML("""
    <script>
      const observer = new MutationObserver(() => {
        const box = document.querySelector('#prompt-box textarea');
        if (box) {
          box.scrollTop = 0;
        }
      });

      const target = document.querySelector('#prompt-box');
      if (target) {
        observer.observe(target, { childList: true, subtree: true });
      }
    </script>
    """)

    def on_generate(*args):
        success_note.visible = True
        prompt, solution, case = process_demo_request(*args)
        return prompt, solution, case, "✅ Task successfully generated. See below."

    submit_btn.click(
        fn=on_generate,
        inputs=[start_task, terminal_task, asset_count_min, asset_count_max, married_percentage, domicile_count_min, domicile_count_max, state_jurisdictions, dataset_size, irrelevant_facts, opinions],
        outputs=[prompt_output, solution_output, case_json, success_note]
    )

if __name__ == '__main__':
    demo.launch()