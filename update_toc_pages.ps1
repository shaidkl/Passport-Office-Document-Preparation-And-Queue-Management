$ErrorActionPreference = "Stop"
$docxPath = Join-Path $PSScriptRoot "Recommendation Report - Supporting Women Entrepreneurs in Nepal.docx"

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $document = $word.Documents.Open($docxPath)
    try {
        $document.Repaginate()
        $headingPages = @{}
        foreach ($paragraph in $document.Paragraphs) {
            $styleName = [string]$paragraph.Range.Style.NameLocal
            if ($styleName -like "Heading*") {
                $headingText = ([string]$paragraph.Range.Text) -replace "[\r\a]", ""
                $headingText = $headingText.Trim()
                if ($headingText) {
                    $headingPages[$headingText] = [int]$paragraph.Range.Information(3)
                }
            }
        }

        $contentsTable = $null
        foreach ($table in $document.Tables) {
            $firstCell = ([string]$table.Cell(1, 1).Range.Text) -replace "[\r\a]", ""
            if ($firstCell.Trim() -eq "Table of Contents") {
                $contentsTable = $table
                break
            }
        }
        if ($null -eq $contentsTable) {
            throw "The contents table could not be found."
        }

        foreach ($row in $contentsTable.Rows) {
            $title = ([string]$row.Cells.Item(1).Range.Text) -replace "[\r\a]", ""
            $title = $title.Trim()
            if ($headingPages.ContainsKey($title)) {
                $row.Cells.Item(3).Range.Text = [string]$headingPages[$title]
            }
        }

        $document.Save()
        Write-Output "Updated visible contents-page dots and page numbers."
        foreach ($key in @("Table of Contents", "Executive Summary", "1. Introduction", "References")) {
            Write-Output ("{0}: {1}" -f $key, $headingPages[$key])
        }
    }
    finally {
        $document.Close(0)
    }
}
finally {
    $word.Quit()
}
