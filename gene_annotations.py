import requests
import pandas as pd
import time
from pathlib import Path
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from collections import defaultdict
import openpyxl
from datetime import datetime
import json
import sys
from bs4 import BeautifulSoup
import random

# Suppress warnings
warnings.filterwarnings("ignore")

class GeneAnnotationTool:
    def __init__(self):
        # Configuration
        self.CACHE_DIR = Path("gene_data_cache")
        self.CACHE_DIR.mkdir(exist_ok=True)
        self.REQUEST_TIMEOUT = 45
        self.MAX_RETRIES = 3
        self.RETRY_DELAY = 2
        self.MAX_WORKERS = 3  # Reduced from original to be API-friendly
        self.PUBMED_API_KEY = None  # Set your NCBI API key here if available
        self.LAST_API_CALL_TIME = 0
        self.MIN_API_INTERVAL = 0.34  # ~3 requests/second (NCBI limit without API key)
        
        # Configure requests session
        self.session = self._configure_session()
        
    def _configure_session(self):
        """Configure requests session with retry logic"""
        session = requests.Session()
        retries = Retry(
            total=self.MAX_RETRIES,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        session.mount("https://", HTTPAdapter(max_retries=retries))
        session.mount("http://", HTTPAdapter(max_retries=retries))
        return session
    
    def _enforce_rate_limit(self):
        """Enforce rate limiting between API calls"""
        elapsed = time.time() - self.LAST_API_CALL_TIME
        if elapsed < self.MIN_API_INTERVAL:
            sleep_time = self.MIN_API_INTERVAL - elapsed + random.uniform(0, 0.1)
            time.sleep(sleep_time)
        self.LAST_API_CALL_TIME = time.time()

    def _make_api_call(self, url, params=None, headers=None):
        """Make API call with rate limiting and retries"""
        self._enforce_rate_limit()
        
        try:
            response = self.session.get(
                url,
                params=params,
                headers=headers,
                timeout=self.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            # Check for PubMed API errors in response
            if "db=pubmed" in url and "error" in response.text.lower():
                error_msg = BeautifulSoup(response.text, 'xml').find('error')
                if error_msg:
                    raise requests.HTTPError(f"PubMed API error: {error_msg.text}")
            
            return response
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {str(e)}", file=sys.stderr)
            raise

    def get_gene_info(self, gene_symbol):
        """Get comprehensive gene information from multiple sources."""
        # Try Ensembl first
        ensembl_data = self._get_ensembl_gene_info(gene_symbol)
        if ensembl_data:
            return ensembl_data
        
        # Fall back to NCBI
        ncbi_data = self._get_ncbi_gene_info(gene_symbol)
        if ncbi_data:
            return ncbi_data
        
        # Final fallback
        return {
            "Gene": gene_symbol,
            "Description": "Not available",
            "Chromosome": "N/A",
            "Genomic Location": "N/A",
            "Gene ID": "N/A",
            "Protein Name": "N/A",
            "Function": "N/A",
            "Source": "No data found",
            "Last Updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def _get_ensembl_gene_info(self, gene_symbol):
        """Get gene info from Ensembl."""
        try:
            url = f"https://rest.ensembl.org/lookup/symbol/homo_sapiens/{gene_symbol}?expand=1"
            headers = {"Content-Type": "application/json"}
            response = self._make_api_call(url, headers=headers)
            data = response.json()
            
            return {
                "Gene": gene_symbol,
                "Description": data.get("description", "N/A").split("[")[0].strip(),
                "Chromosome": data.get("seq_region_name", "N/A"),
                "Genomic Location": f"{data.get('start', 'N/A'):,}-{data.get('end', 'N/A'):,}",
                "Gene ID": data.get("id", "N/A"),
                "Protein Name": data.get("display_name", "N/A"),
                "Function": "See UniProt for detailed function",
                "Source": "Ensembl",
                "Last Updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            print(f"Ensembl failed for {gene_symbol}: {str(e)}", file=sys.stderr)
            return None

    def _get_ncbi_gene_info(self, gene_symbol):
        """Get gene info from NCBI."""
        try:
            # Search for gene ID
            search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            search_params = {
                "db": "gene",
                "term": f"{gene_symbol}[Gene Name] AND human[Organism]",
                "retmode": "json",
                "api_key": self.PUBMED_API_KEY
            }
            response = self._make_api_call(search_url, params=search_params)
            search_data = response.json()
            
            if not search_data.get("esearchresult", {}).get("idlist"):
                return None
            
            gene_id = search_data["esearchresult"]["idlist"][0]
            
            # Get gene summary
            summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
            summary_params = {
                "db": "gene",
                "id": gene_id,
                "retmode": "json",
                "api_key": self.PUBMED_API_KEY
            }
            response = self._make_api_call(summary_url, params=summary_params)
            gene_data = response.json()
            
            return {
                "Gene": gene_symbol,
                "Description": gene_data.get("result", {}).get(gene_id, {}).get("summary", "N/A"),
                "Chromosome": gene_data.get("result", {}).get(gene_id, {}).get("chromosome", "N/A"),
                "Genomic Location": "N/A",
                "Gene ID": gene_id,
                "Protein Name": "N/A",
                "Function": gene_data.get("result", {}).get(gene_id, {}).get("summary", "N/A")[:200] + "..." if gene_data.get("result", {}).get(gene_id, {}).get("summary") else "N/A",
                "Source": "NCBI",
                "Last Updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            print(f"NCBI failed for {gene_symbol}: {str(e)}", file=sys.stderr)
            return None

    def get_literature(self, gene_symbol, max_results=5):
        """Get recent literature from PubMed with abstracts and keywords."""
        try:
            # Search for articles
            search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            search_params = {
                "db": "pubmed",
                "term": f"{gene_symbol}[Title/Abstract] OR {gene_symbol}[MeSH Terms] OR {gene_symbol}[Keyword]",
                "retmax": max_results,
                "sort": "relevance",
                "retmode": "json",
                "api_key": self.PUBMED_API_KEY
            }
            response = self._make_api_call(search_url, params=search_params)
            search_data = response.json()
            
            literature = []
            if search_data.get("esearchresult", {}).get("idlist"):
                pmids = search_data["esearchresult"]["idlist"]
                
                # Get detailed article information
                fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
                fetch_params = {
                    "db": "pubmed",
                    "id": ",".join(pmids),
                    "retmode": "xml",
                    "rettype": "abstract",
                    "api_key": self.PUBMED_API_KEY
                }
                response = self._make_api_call(fetch_url, params=fetch_params)
                
                # Parse XML response
                soup = BeautifulSoup(response.text, 'xml')
                
                for article in soup.find_all('PubmedArticle'):
                    pmid = article.find('PMID').text if article.find('PMID') else "N/A"
                    title = article.find('ArticleTitle').text if article.find('ArticleTitle') else "N/A"
                    
                    # Get abstract
                    abstract = ""
                    abstract_section = article.find('Abstract')
                    if abstract_section:
                        abstract = ' '.join([text.text for text in abstract_section.find_all('AbstractText')])
                    
                    # Get keywords
                    keywords = []
                    keyword_list = article.find('KeywordList')
                    if keyword_list:
                        keywords = [kw.text for kw in keyword_list.find_all('Keyword')]
                    
                    # Get authors
                    authors = []
                    author_list = article.find('AuthorList')
                    if author_list:
                        authors = [f"{auth.find('LastName').text if auth.find('LastName') else ''}, "
                                  f"{auth.find('ForeName').text if auth.find('ForeName') else ''}" 
                                  for auth in author_list.find_all('Author')]
                    first_author = authors[0] if authors else "N/A"
                    
                    # Get journal info
                    journal = article.find('Journal')
                    journal_title = journal.find('Title').text if journal and journal.find('Title') else "N/A"
                    pub_date = journal.find('PubDate') 
                    year = pub_date.find('Year').text if pub_date and pub_date.find('Year') else "N/A"
                    month = pub_date.find('Month').text if pub_date and pub_date.find('Month') else ""
                    day = pub_date.find('Day').text if pub_date and pub_date.find('Day') else ""
                    pub_date_str = f"{year}-{month}-{day}" if (year or month or day) else "N/A"
                    
                    # Get DOI
                    article_id = article.find('ArticleId', IdType="doi")
                    doi = article_id.text if article_id else "N/A"
                    
                    literature.append({
                        "Gene": gene_symbol,
                        "PMID": pmid,
                        "Title": title,
                        "First Author": first_author,
                        "Authors": "; ".join(authors) if authors else "N/A",
                        "Journal": journal_title,
                        "Publication Date": pub_date_str,
                        "Abstract": abstract[:1000] + "..." if len(abstract) > 1000 else abstract or "N/A",
                        "Keywords": "; ".join(keywords) if keywords else "N/A",
                        "DOI": doi,
                        "Source": "PubMed"
                    })
            
            return literature[:max_results]
        except Exception as e:
            print(f"PubMed failed for {gene_symbol}: {str(e)}", file=sys.stderr)
            return []

    # [Rest of the methods remain unchanged...]
    
    def process_genes(self, genes, config):
        """Process multiple genes with improved PubMed API handling"""
        all_results = defaultdict(list)
        start_time = time.time()
        
        # Process genes sequentially if literature is needed to avoid PubMed rate limits
        if config.get("max_literature", 0) > 0:
            print("Processing genes sequentially due to PubMed API rate limits...")
            for gene in tqdm(genes, desc="Processing genes"):
                try:
                    result = self.process_gene(gene, config)
                    for key, value in result.items():
                        if value:
                            if isinstance(value, list):
                                all_results[key].extend(value)
                            else:
                                all_results[key].append(value)
                except Exception as e:
                    print(f"Error processing gene {gene}: {str(e)}", file=sys.stderr)
        else:
            # Use parallel processing for other data
            with ThreadPoolExecutor(max_workers=config["MAX_WORKERS"]) as executor:
                futures = {executor.submit(self.process_gene, gene, config): gene for gene in genes}
                
                for future in tqdm(as_completed(futures), total=len(genes), desc="Processing genes"):
                    gene = futures[future]
                    try:
                        result = future.result()
                        for key, value in result.items():
                            if value:
                                if isinstance(value, list):
                                    all_results[key].extend(value)
                                else:
                                    all_results[key].append(value)
                    except Exception as e:
                        print(f"Error processing gene {gene}: {str(e)}", file=sys.stderr)
        
        return dict(all_results)
