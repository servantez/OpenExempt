# OpenExempt: a Diagnostic Benchmark for Legal Reasoning

This work is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

Requires Python version 3.10 or later.

## Benchmark Overview
Language models are increasingly being deployed in the legal domain where their limitations, especially those unknown, pose a significant risk. Existing legal reasoning benchmarks have provided useful insights into the capabilities of these models, but static question-answer pairs can conflate reasoning errors in legal tasks requiring multiple reasoning skills. Diagnostic tests can help assess the limits of these models by allowing for incremental adjustments to task complexity across many dimensions, and by unraveling complex tasks into subtasks to isolate specific types of reasoning. We present OpenExempt, a diagnostic benchmark for legal reasoning, which enables fine-grain control over crafting legal scenarios. OpenExempt represents statutes and cases both in natural language and in structured form. This approach not only enables the creation of new cases on demand, but also makes the solutions to these cases machine computable.

An overview of OpenExempt's dynamic task construction pipeline can be seen below.

![OpenExempt System](OE_system.png)

## Asset Exemption under the Bankruptcy Code
OpenExempt is named for its central task, exempting assets under the United States Bankruptcy Code. A person filing for bankruptcy, called the Debtor, is allowed to protect certain property from seizure by creditors. An exemption defines a category of property which can be protected - for example, up to $4,450 in a motor vehicle. Each state defines its own exemption statutes which differ considerably in regards to which assets are protected. The debtor may claim state or federal exemptions, unless their state specifically prohibits the use of federal exemptions, known as "opt-out". Which state exemption laws apply to a given case is determined by where the debtor lived prior to filing.

## Getting Started
Clone the repo:

```bash
git clone https://github.com/servantez/OpenExempt.git
```

Navigate to project directory:

```bash
cd OpenExempt
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the benchmark:

```bash
python open_exempt.py -d dataset_name
```
Replace `dataset_name` with your preferred name. You can also specify two optional arguments: `-c` to specify the path to your config file (if you are not using the default), and the `-v` flag for verbose logging. This command will construct a dataset based on the settings in your config file, and output the dataset to the `/data/tasks/` directory. See below for details on setting the config file.

## Benchmark Configuration

Benchmark users are able to control the legal tasks specified in the dataset by setting a range of arguments in the config file. The default configuration file is located at config.json in the project root directory. The table below provides an overview of OpenExempt's configuration arguments.



| Argument | Description |
|:----------|:-------------|
| Start and terminal task | The process of exempting assets under the Bankruptcy Code involves a sequence of intermediate subtasks. In addition to evaluating the entire exemption process, benchmark users can select a single subtask or any sequential interval of subtasks. See the web interface for a description of subtasks. | 
| State jurisdictions | The specific state jurisdictions which should be involved in the cases being generated. All datasets include the federal statutes. | 
| Minimum and maximum asset count | The upper and lower bound for the number of assets that should be included in each case. | 
| Obfuscation facts | Language models can be susceptible to making errors when the input context includes irrelevant information or opinions. This arguments injects obfuscation facts into the task to gain insights on resulting hallucinations and sycophancy. | 
| Percentage of married cases | The dollar amount protected under a given exemption typically increases for married couples. This argument indicates the percentage of cases which should involve married individuals. | 
| Minimum and maximum domicile count | The upper and lower bound for the number of prior residences of the Debtor before filing. | 
| Dataset size | The number of tasks and solutions in the dataset. | 
