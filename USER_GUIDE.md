# Gene Analysis Toolkit - User Guide

## Table of Contents
1. [Gene Annotation Tool](#gene-annotation-tool)
2. [Enrichment Analysis](#enrichment-analysis)
3. [Primer Design](#primer-design)
4. [Troubleshooting](#troubleshooting)
5. [Best Practices](#best-practices)

---

## Gene Annotation Tool

### Input Requirements
- **Format**: Comma-separated gene symbols (e.g., `BRCA1, TP53, MBP`)
- **Validation**: Only HGNC-approved symbols will return results

### Recommended Settings
| Parameter | Default | Recommended Range | Description |
|-----------|---------|-------------------|-------------|
| Max Variants | 10 | 5-15 | ClinVar variants per gene |
| Max Trials | 5 | 3-10 | Clinical trials to retrieve |
| Max Literature | 5 | 3-10 | PubMed articles to fetch |
| Threads | 3 | 2-5 | Parallel processing threads |

### Output Interpretation
- **Gene Info Tab**: Basic gene characteristics from Ensembl/NCBI
- **Variants Tab**: ClinVar variants with clinical significance
- **Clinical Trials Tab**: Active trials from ClinicalTrials.gov
- **Literature Tab**: Recent publications with abstracts

### Pro Tip
> Use the Excel export for literature review - it preserves hyperlinks to PMIDs and DOIs

---

## Enrichment Analysis

### Input Methods
1. **File Upload**:
   - Accepts `.txt` (one gene per line) or `.csv` (single column)
   - Max file size: 5MB

2. **Paste Gene List**:
   - Supports both newline and comma separation
   - Example format:
     ```
     BRCA1
     TP53
     MBP
     ```

### Analysis Parameters
- **Databases**:
  - KEGG Pathways
  - Reactome Pathways
  - Gene Ontology (BP, MF, CC)

### Understanding Results
- **Significance Threshold**: FDR < 0.1 (red dashed line in plots)
- **Plot Elements**:
  - Dot size = Combined Score
  - Color intensity = -log10(adj. p-value)

### Report Features
- **HTML Report** includes:
  - All significant terms
  - Methods section for publications
  - Interactive tables

---

## Primer Design

### Optimal Parameters
| Parameter | Ideal Value | Acceptable Range |
|-----------|-------------|------------------|
| GC Content | 50% | 40-60% |
| Product Size | 200bp | 100-300bp |
| Tm Difference | <2°C | <5°C |
| Primer Length | 20bp | 18-24bp |

### Validation Criteria
The tool checks for:
1. Self-dimers (forward-forward, reverse-reverse)
2. Primer-dimers (forward-reverse)
3. Poly-X sequences (>3 identical bases)
4. GC clamp (at least 1 G/C in last 5 bases)

### Result Interpretation
| Status Icon | Meaning | Action Required |
|-------------|---------|------------------|
| ✅ Valid | Passed all checks | Ready to order |
| ⚠️ Check | Minor issues | Review warnings |
| ❌ Failed | Critical problems | Redesign needed |

### Troubleshooting Failed Designs
1. **High GC%**: Adjust slider to 45-55%
2. **Tm Mismatch**: Reduce product size range
3. **Poly-X Warnings**: Manually edit sequences if needed

---

## Troubleshooting

### Common Issues
| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| No results | Invalid gene symbols | Check HGNC database |
| Slow loading | Many genes/threads | Reduce to 5 genes, 2 threads |
| API errors | NCBI rate limit | Wait 1 minute and retry |
| Blank plots | No significant terms | Try different databases |

### Error Messages
- **"NCBI API Failed"**: Check internet connection and Entrez.email
- **"No Valid Genes"**: Verify symbols with [HGNC](https://www.genenames.org)
- **"Design Failed"**: Adjust parameters or try manual design

---

## Best Practices

### For High-Throughput Analysis
1. **Gene Annotation**:
   - Process in batches of 10 genes
   - Use 4 threads for optimal speed

2. **Enrichment**:
   - Pre-filter genes with p-value < 0.05
   - Focus on KEGG+Reactome for pathways

3. **Primer Design**:
   - Design 3 pairs per gene
   - Order from multiple algorithms

### Publication-Ready Results
1. Always include:
   - Database versions used
   - Analysis parameters (FDR threshold)
   - Tool version number (found in app footer)

2. For primers:
   - Include validation metrics (GC%, Tm)
   - Verify with gel electrophoresis

---

## Support
For additional help:
- Email: SALMALOUKMAN37@gmail.com
- GitHub Issues: [New Issue](https://github.com/Salma2306/gene-analysis-toolkit/issues)

*Last Updated: 2025-07-15*