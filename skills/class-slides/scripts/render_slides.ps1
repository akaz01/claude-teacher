param(
    [Parameter(Mandatory = $true)][string]$Deck,
    [Parameter(Mandatory = $true)][string]$OutDir,
    [int]$Width = 1280,
    [int]$Height = 720
)
# Export every slide of a .pptx to PNG with PowerPoint (Windows only), for visual review.
# Usage: powershell -File render_slides.ps1 lesson.pptx out_folder
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force $OutDir | Out-Null
$out = (Resolve-Path -LiteralPath $OutDir).Path
$app = New-Object -ComObject PowerPoint.Application
$alreadyOpen = $app.Presentations.Count  # never close a PowerPoint the teacher is using
$presentation = $null
try {
    $presentation = $app.Presentations.Open((Resolve-Path -LiteralPath $Deck).Path, $true, $false, $false)
    $index = 1
    foreach ($slide in $presentation.Slides) {
        $slide.Export((Join-Path $out ("s{0:D2}.png" -f $index)), "PNG", $Width, $Height)
        $index++
    }
    Write-Output "exported $($index - 1) slides to $out"
} finally {
    if ($null -ne $presentation) { $presentation.Close() }
    if ($alreadyOpen -eq 0) { $app.Quit() }
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null
}
