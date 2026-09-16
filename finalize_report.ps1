$ErrorActionPreference = "Stop"
$docxPath = Join-Path $PSScriptRoot "Recommendation Report - Supporting Women Entrepreneurs in Nepal.docx"
$pdfPath = Join-Path $PSScriptRoot "Recommendation Report - Supporting Women Entrepreneurs in Nepal.pdf"

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $document = $word.Documents.Open($docxPath)
    try {
        foreach ($toc in $document.TablesOfContents) {
            $toc.Update()
        }
        foreach ($field in $document.Fields) {
            $null = $field.Update()
        }
        $document.Save()
        $document.ExportAsFixedFormat($pdfPath, 17)
    }
    finally {
        $document.Close(0)
    }
}
finally {
    $word.Quit()
}

Get-Item $docxPath, $pdfPath | Select-Object FullName, Length, LastWriteTime
