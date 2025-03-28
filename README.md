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
Replace `dataset_name` with your preferred name.

## Benchmark Configuration
config.json in the root directory 

# Adding New Statutes and Assets
OpenExempt is easily exstensible.
