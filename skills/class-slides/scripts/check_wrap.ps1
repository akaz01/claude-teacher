param(
    [Parameter(Mandatory = $true)][string]$Deck,
    [double]$OrphanRatio = 0.3
)
# Count the real line wraps PowerPoint makes (Windows only).
# Writes wraps.tsv next to the deck: slide, shape, lines, first line length, last line length, text.
# Prints paragraphs whose last line is short (only a few letters wrapped) - widen the box or shorten the text.
# Usage: powershell -File check_wrap.ps1 lesson.pptx
$ErrorActionPreference = "Stop"
$deckPath = (Resolve-Path -LiteralPath $Deck).Path
$rows = New-Object System.Collections.Generic.List[string]
$script:orphans = 0

function Visit($shape, $slideNo) {
    if ($shape.Type -eq 6) { foreach ($inner in $shape.GroupItems) { Visit $inner $slideNo }; return }
    if (-not $shape.HasTextFrame) { return }
    $range = $shape.TextFrame2.TextRange
    for ($i = 1; $i -le $range.Paragraphs().Count; $i++) {
        $paragraph = $range.Paragraphs($i)
        $text = $paragraph.Text.Trim()
        if ($text.Length -eq 0) { continue }
        $lines = $paragraph.Lines().Count
        if ($lines -lt 2) { continue }
        $first = $paragraph.Lines(1).Text.Trim().Length
        $last = $paragraph.Lines($lines).Text.Trim().Length
        $rows.Add("$slideNo`t$($shape.Name)`t$lines`t$first`t$last`t$text")
        if ($last -le $first * $OrphanRatio) {
            $script:orphans++
            Write-Output "slide $slideNo [$($shape.Name)] last line $last of $first chars: $text"
        }
    }
}

$app = New-Object -ComObject PowerPoint.Application
$alreadyOpen = $app.Presentations.Count  # never close a PowerPoint the teacher is using
try {
    $presentation = $app.Presentations.Open($deckPath, $true, $false, $false)
    $slideNo = 1
    foreach ($slide in $presentation.Slides) {
        foreach ($shape in $slide.Shapes) { Visit $shape $slideNo }
        $slideNo++
    }
    $presentation.Close()
} finally {
    if ($alreadyOpen -eq 0) { $app.Quit() }
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null
}
$tsv = Join-Path (Split-Path $deckPath) "wraps.tsv"
[System.IO.File]::WriteAllLines($tsv, $rows, [System.Text.UTF8Encoding]::new($false))
Write-Output "short last lines: $($script:orphans) (details: $tsv)"
