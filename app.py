import json
import gradio as gr
from open_exempt import generate_demo
from source.config import Config
from source.task_id import TaskID


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

# Create the interface
with gr.Blocks(css=".gray-bg {background-color: #e5e5e5 !important;}") as demo:
    gr.Markdown("# OpenExempt: a Diagnostic Benchmark for Legal Reasoning")
    gr.Markdown("OpenExempt is a dynamic legal reasoning benchmark which gives users control over crafting legal scenarios through a set of configuration options. This interface is a demo to illustrate the benchmark's ability to construct tasks and solutions on demand, allowing users to easily set these configuration options and create a single example.")
    gr.HTML("<div style='height: 1px;'></div>")
    
    with gr.Row():
        with gr.Column():
            gr.Markdown("# Benchmark Overview")
            gr.Markdown(" OpenExempt is named for its central task, exempting assets under the United States Bankruptcy Code. A person filing for bankruptcy, called the Debtor, is allowed to protect certain property from seizure by creditors. An exemption defines a category of property which can be protected - for example, up to $4,450 in a motor vehicle. Each state defines its own exemption statutes which differ considerably in regards to which assets are protected. The debtor may claim state or federal exemptions, unless their state specifically prohibits the use of federal exemptions, known as \"opt-out\". Which state exemption laws apply to a given case is determined by where the debtor lived prior to filing.")
        with gr.Column():
            gr.Image(value="OE_exemption.png", elem_classes="gray-bg", show_label=False, height=340, width=460)

    gr.HTML("<div style='height: 1px;'></div>")
    gr.Markdown("# Task Scope")
    gr.Markdown("The process of exempting assets involves a sequence of subtasks - each requiring different types of reasoning. OpenExempt enables users to evaluate the entire exemption process, a single subtask, or any sequential interval of subtasks to examine specific combinations of reasoning skills.")
    gr.HTML("<div style='height: 1px;'></div>")

    with gr.Row():
        with gr.Column():
            gr.Markdown("## Subtasks")
            gr.Markdown("**Select governing exemption laws.** To determine which state exemptions a debtor is allowed to claim, the Bankruptcy code considers which states the debtor has lived in the preceding 730 days. This task requires identifying the governing jurisdiction given residency dates and locations.")
            gr.Markdown("**Asset Exemption (categorization).** This task involves identifying applicable exemptions for each asset based on the governing state exemption laws. This is a multi-label classification problem since multiple exemptions can apply to a single asset. Federal exemptions may also need to be considered depending on whether the corresponding state has opted-out.")
            gr.Markdown("**Asset exemption (dollar value).** For the selected state exemptions, and federal exemptions if applicable, determine how much of the fair market value of each asset is protected.")
            gr.Markdown("**Identify non-exempt assets.** Based on the optimal exemptions that can be claimed, determine the total dollar value of assets not protected under the exemption laws of each applicable jurisdiction.")
            gr.Markdown("**Select optimal exemptions.** Select the optimal exemption set by minimizing the dollar value of non-exempt assets.")
            
        with gr.Column():
            gr.Image(value="OE_tasks.png", show_label=False)

    gr.HTML("<div style='height: 10px;'></div>")
    gr.Markdown("# Benchmark Configuration")
    gr.Markdown("**Define the task scope** (see subtask descriptions above)")

    with gr.Row():
        with gr.Column():
            start_task = gr.Radio(choices=TaskID.supported_tasks() , value=TaskID.GOVERNING_JURISDICTIONS.display_name(), label="Select Start Task")
        with gr.Column():
            terminal_task = gr.Radio(choices=TaskID.supported_tasks() , value=TaskID.OPTIMAL_EXEMPTIONS.display_name(), label="Select Terminal Task", info="(Must be greater than or equal to start task)")

    gr.Markdown("**Choose the state jurisdictions that will be involved in the cases**")
    state_jurisdictions = gr.CheckboxGroup(choices=config.state_jurisdictions, value=config.state_jurisdictions, label="Select State Jurisdictions", info="Must select at least one state jurisdiction")
            
    with gr.Row():
        with gr.Column():
            married_percentage = gr.Slider(value=config.married_percentage * 100, label="Percentage of married cases", minimum=0, maximum=100, step=10)
            domicile_count_min = gr.Number(value=config.domicile_count_min, label="Minimum Number of Prior Residences", info='(Min: 1, Max: 5)', minimum=1, maximum=5)
            domicile_count_max = gr.Number(value=config.domicile_count_max, label="Maximum Number of Prior Residences", info='(Must be greater than or equal to Minimum Domicile Count, Max: 5)', minimum=1, maximum=5)

        with gr.Column():
            asset_count_min = gr.Number(value=config.asset_count_min, label="Minimum Number of Assets", info='(Min: 1, Max: 10)', minimum=1, maximum=10)
            asset_count_max = gr.Number(value=config.asset_count_max, label="Maximum Number of Assets", info='(Must be greater than or equal to Minimum Asset Count, Max: 10)', minimum=1, maximum=10)
            dataset_size = gr.Number(value=1, label="Dataset Size", info='(abridged to one example for demo purposes)', minimum=1)

    gr.Markdown("**Obfuscation Statements**")
    with gr.Row():
        with gr.Column():
            irrelevant_facts = gr.CheckboxGroup(choices=["Irrelevant Asset Facts", "Irrelevant Domicile Facts"], value=[], label="Obfuscation Facts", info="Add irrelevant facts to test robustness of reasoning")
        with gr.Column():
            opinions = gr.CheckboxGroup(choices=["Asset Opinions", "Domicile Opinions"], value=[], label="Opinions", info="Add opinions to test sycophancy")

    gr.Markdown("Build notes: this demo is still in alpha so please report any issues observed. \nKnown issues:\n None.")
    
    submit_btn = gr.Button("Generate Task", variant="primary")
    
    prompt_output = gr.Textbox(label="Prompt")
    solution_output = gr.JSON(label="Solution")
    case_output = gr.JSON(label="Case")
    
    submit_btn.click(
        fn=process_demo_request,
        inputs=[start_task, terminal_task, asset_count_min, asset_count_max, married_percentage, domicile_count_min, domicile_count_max, state_jurisdictions, dataset_size, irrelevant_facts, opinions],
        outputs=[prompt_output, solution_output, case_output]
    )

demo.launch()