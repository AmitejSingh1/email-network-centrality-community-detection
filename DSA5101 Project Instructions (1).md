# **<u>Project Instructions</u>** 

Apply at least two distinct classes of algorithms from the course to one dataset, using them to investigate a coherent research question. 

You may choose or adapt one of the three examples in this document, or select your own dataset and formulate your own problem statement. All projects follow the same requirements and grading criteria. 

## **<u>Mandatory components</u>** 

**One dataset:** Use one publicly accessible dataset that is free to download. Multiple files, metadata and labels supplied as part of that dataset count as one dataset. Subsets, traintest splits and derived representations are allowed; do not combine independently sourced datasets. 

**Research question:** State a clear question that the available data can help answer. Explain why it is useful or interesting. 

**Algorithms:** Apply at least two distinct algorithm classes covered in the lectures. Name the classes and relevant lectures. K-means and hierarchical clustering count as one clustering class; PageRank and Louvain count as two. Routine preprocessing (such as cleaning and standardization), evaluation measures and parameter variations do not count as additional classes. 

**Combined analysis:** Explain how the methods together address your question. They may form a pipeline or provide complementary evidence. Preparing the data and connecting the methods are part of your project work. 

**Evaluation:** Use appropriate evaluation measures, at least one meaningful baseline or comparison, and at least one sensitivity or robustness check. Choose evaluation suited to your task. For predictive tasks, keep final test data separate from fitting and parameter selection. 

**Findings:** Support your findings with results and discuss limitations. Negative or inconclusive findings are acceptable when the analysis and interpretation are sound. 

1 

**Reproducibility:** Record the dataset source and working subset, preprocessing, important parameters, random seeds where applicable and software versions. Cite datasets, guides and any adapted code. 

### **Practical scope** 

Use popular Python libraries for the core algorithms; implementations from scratch are not required. The work should be manageable within approximately two weeks on an ordinary laptop with around 8 GB RAM. Use in-memory processing on a single laptop; MapReduce and distributed computing are outside the project scope. 

## **<u>Grading criteria</u>** 

Assessment considers the following criteria across both the report and the supporting implementation. 

|**Criterion**|**What the assessment considers**|
|---|---|
|Problem formulation and<br>data preparation|A clear, answerable question; an appropriate data<br>representation; and justified cleaning and selection<br>decisions.|
|Application and<br>understanding of<br>algorithms|Appropriate methods, correct library use, and an<br>explanation of the assumptions and parameters that matter<br>for the analysis.|
|Connection between<br>methods|A coherent combined analysis and a clear explanation of<br>how each method contributes to answering the research<br>question.|
|Evaluation and<br>robustness|Relevant metrics and comparisons, checks of stability or<br>sensitivity, and an evaluation design that supports the<br>conclusions.|
|Insights and limitations|Findings supported by results, thoughtful interpretation,<br>and recognition of what the data and methods cannot<br>establish.|



2 

|**Criterion**|**What the assessment considers**|
|---|---|
|Communication and<br>reproducibility|A clear report, readable figures and tables, and an<br>understandable implementation with enough detail to<br>reproduce the analysis.|



## **<u>Assessment philosophy</u>** 

A project based on a supplied example can earn full marks. A self-sourced project is assessed by the same criteria; selecting a new dataset does not automatically earn additional credit. 

Credit comes from sound reasoning, correct implementation and evidence-supported conclusions. Larger datasets, more algorithms and more complicated code do not automatically improve the grade. 

A well-supported negative finding can be valuable. Explain what you learned from the results, including why an expected relationship or improvement did not appear. 

Explain and justify the choices relevant to your project. Extensive reproduction of textbook theory is unnecessary. The report should make the reasoning behind the analysis easy to assess. 

## **<u>Submission format</u>** 

Submit one ZIP file named with your NUS matriculation number, for example A0123456X.zip. Do **not** include your name in the submission. Include exactly the following three files at the top level of the ZIP. 

|**File**|**Required contents**|
|---|---|
|report.pdf|The primary assessed document, containing the research question,<br>methods, results, interpretation and limitations.|
|analysis.ipynb|An executed notebook containing the analysis code, relevant<br>outputs and figures, and instructions for obtaining the data.|



3 

|**File**|**Required contents**|
|---|---|
||List the Python packages and versions needed to run the notebook.<br>The notebook must be executable from beginning to end after the|
|requirements.txt|required packages are installed and the dataset is obtained using<br>the instructions provided. Selected submissions may be rerun for<br>verification.|



### **Report length and structure** 

The main report **must not exceed eight pages** , including the opening summary, Sections 1–6, figures, tables, captions and labels. The report must use A4 page size, margins of at least 2 cm on all sides, and a minimum 10-point font for body text. The reference list is excluded from the page limit. Appendices are not permitted; any material intended for assessment must appear within the eight-page report. The notebook is not subject to this page limit. Submissions that do not comply with these formatting requirements may be penalized. 

Begin with a small summary table identifying the project title, dataset and source, algorithm classes, and research question. Then use these section headings: 

- 1 Research question and dataset 

- 2 Data preparation 

- 3 Methods and how they connect 

- 4 Evaluation and results 

- 5 Insights and limitations 

- 6 Reproducibility information 

References 

### **Readable evidence** 

Submit a PDF with selectable body text and table contents, page numbers, and legible figures with captions and labels. Figures may be embedded as images. Do not scan the entire report or replace tables with screenshots. Include all findings you want assessed in the report; the notebook supplies implementation evidence. External dashboards, videos or websites must not be needed to understand the submission. 

4 

### **Notebook and data** 

Restart the notebook kernel, run all cells in order and save the relevant outputs before submission. Keep outputs concise and organize the notebook into clearly labeled sections. Record the Python version and the exact data version or period, subset rules and download instructions. Do not include raw data in the ZIP. Provide the dataset download link and sufficient instructions or code in the notebook to recreate the working dataset, including any filtering, sampling and preprocessing. 

5 

## **<u>Example 1: Product bundles for different customers</u>** 

Which product bundles might appeal to different types of customers? 

**Dataset:** <u>UCI Online Retail, containing 541,909 transaction line items with customer,</u> product and purchase information. 

**Methods:** Clustering (Lecture 3) + frequent itemset mining and association rules (Lecture 1). 

**Suggested approach:** Explore customer segments based on purchasing behavior and investigate whether they exhibit different patterns of products bought together. Use these patterns to propose product bundles or promotions tailored to particular segments. 

**Insights to investigate:** Are there product associations that are strong within a particular customer segment but overlooked in the overall data? Does a strong storewide association mainly reflect the behavior of one group? How could these differences affect a retailer’s choice of bundles? 

**Evaluation:** Consider measures such as support, confidence and interest when assessing product associations. Compare segment-specific findings with patterns in the overall data, and investigate whether the main conclusions remain stable under reasonable changes to the analysis. 

**Suggested scope:** Choose a manageable working set of customers and products, documenting any filtering. Focus on a few interpretable segments and product associations with a clear business interpretation. 

### **Implementation resources** 

- <u>scikit-learn K-means worked example</u> 

- mlxtend Apriori examples 

- mlxtend <u>association rule examples</u> 

- Practical Business Python market <u>basket tutorial</u> 

6 

## **<u>Example 2: Movies with strong appeal to particular audiences</u>** 

Which movies are hidden gems for particular audiences? 

**Dataset:** MovieLens 100K, containing 100,000 movie ratings. 

**Methods:** Regularized matrix factorization (Lecture 5) + clustering (Lecture 3). 

**Suggested approach:** Use matrix factorization to model user preferences and predict ratings, and clustering to explore differences between audience groups. Investigate films with strong predicted appeal to a particular audience despite receiving relatively little attention in the dataset. Define and justify what counts as a “hidden gem.” 

**Insights to investigate:** Which less frequently rated films appear promising for particular audiences? Which films appeal across several taste groups, and which divide audiences? How might these findings help viewers discover films beyond the most popular choices? 

**Evaluation:** Assess rating prediction accuracy using a suitable error measure, such as RMSE, and compare it with a simple baseline. Examine the evidence supporting the proposed hidden gems within their intended audiences, and investigate whether the main findings are stable under reasonable changes to the model or audience grouping. 

**Suggested scope:** The full dataset is suitable for this project. Focus on a manageable set of audience groups and film examples, explaining both the potential value of the findings and the limits of the available evidence. 

### **Implementation resources** 

- <u>Surprise Getting Started tutorial</u> 

- <u>Surprise matrix factorization reference</u> 

- <u>Surprise FAQ and worked examples</u> 

- <u>scikit-learn K-means worked example</u> 

7 

## **<u>Example 3: Centrality and communities in an email network</u>** 

Who is central in the network, and do communication groups follow department boundaries? 

**Dataset:** Email-Eu-core, containing 1,005 members and 25,571 directed email links from a European research institution, with membership labels for 42 departments. 

**Methods:** PageRank (Lecture 6) + graph clustering or community detection (Lecture 7). 

**Suggested approach:** Use PageRank to investigate which individuals are prominent in the email network, and graph clustering to identify communication communities. Explore how highly ranked individuals are positioned within and between communities, and how these communities relate to department membership. 

**Insights to investigate:** Do people contacted by many others also have the highest PageRank? Do communication communities follow department boundaries or reveal groups spanning departments? Are highly ranked individuals mainly connected within their own community or across community boundaries? 

**Evaluation:** Examine the relationship between PageRank and a simple connectivity measure, such as in-degree. Assess community quality using a suitable measure, such as conductance, and compare the communities with department labels. Investigate whether the main findings remain stable under reasonable changes to the analysis. 

**Suggested scope:** Focus on a few informative comparisons and selected individuals or communities, explaining what the observed network patterns might—and might not— reveal about communication within the institution. 

### **Implementation resources** 

- NetworkX introductory <u>tutorial</u> 

- NetworkX edge list <u>examples and reference</u> 

- NetworkX PageRank example <u>and reference</u> 

- NetworkX Louvain example <u>and reference</u> 

- NetworkX conductance reference 

- <u>SciPy Spearman correlation reference</u> 

8 

