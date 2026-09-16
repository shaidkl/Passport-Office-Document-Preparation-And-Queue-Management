from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

path = Path(__file__).resolve().parent / "Recommendation Report - Supporting Women Entrepreneurs in Nepal.docx"
with zipfile.ZipFile(path) as package:
    document_xml = package.read("word/document.xml")
    root = ET.fromstring(document_xml)

ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
paragraphs = [
    "".join(node.text or "" for node in paragraph.findall(".//w:t", ns))
    for paragraph in root.findall(".//w:p", ns)
]
start = [i for i, text in enumerate(paragraphs) if text == "Executive Summary"][-1]
end = [i for i, text in enumerate(paragraphs) if text == "Appendix A: Action Plan"][-1]
main_text = " ".join(paragraphs[start:end])
words = re.findall(r"\b[\w’'-]+\b", main_text, flags=re.UNICODE)
required = [
    "Executive Summary",
    "1. Introduction",
    "2. Methodology",
    "3. Main Findings",
    "4. Recommendations and Discussion",
    "5. Next Steps and Conclusion",
    "Appendix A: Action Plan",
    "Appendix B: Presentation Guide",
    "References",
]

print(f"File: {path}")
print(f"Main-text words: {len(words)}")
print(f"Required sections present: {all(item in paragraphs for item in required)}")
print(f"Reference entries: {sum(1 for p in paragraphs if p.endswith('Available online'))}")
print(f"Visible dotted TOC rows: {document_xml.count(b'........................')}")
