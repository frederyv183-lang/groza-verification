cd C:\Users\Major\groza

$base = "https://weather.uwyo.edu/cgi-bin/sounding"
$out_dir = "data\raw\sounding"
New-Item -ItemType Directory -Force -Path $out_dir | Out-Null

# Латинские сокращения месяцев — жёстко прописаны
$months = @{
    1  = "Jan"; 2  = "Feb"; 3  = "Mar"; 4  = "Apr"
    5  = "May"; 6  = "Jun"; 7  = "Jul"; 8  = "Aug"
    9  = "Sep"; 10 = "Oct"; 11 = "Nov"; 12 = "Dec"
}

$years = @(2020, 2021, 2022, 2023, 2024, 2025, 2026)

foreach ($year in $years) {
    for ($m = 1; $m -le 12; $m++) {
        if ($year -eq 2026 -and $m -gt 10) { continue }

        $month_en = $months[$m]
        $month_str = "{0:D2}" -f $m

        # STNM=27612, region=europe, TEXT:LIST
        $url = "$base" + "?region=europe&TYPE=TEXT%3ALIST&YEAR=$year&MONTH=$month_en&FROM=0000&TO=1200&STNM=27612"

        $out = Join-Path $out_dir "27612_${year}_${month_str}.txt"

        Write-Host "Скачиваю $year-$month_str ($month_en) ..." -ForegroundColor Cyan

        # Используем curl.exe — он стабильнее и не боится кодировок
        curl.exe --silent --show-error --max-time 60 -o $out $url

        if (Test-Path $out) {
            $size = (Get-Item $out).Length
            if ($size -gt 1000) {
                Write-Host "  OK: $size bytes" -ForegroundColor Green
            } else {
                Write-Host "  ПУСТО/ОШИБКА: $size bytes" -ForegroundColor Red
                Remove-Item $out -ErrorAction SilentlyContinue
            }
        } else {
            Write-Host "  НЕ СОЗДАН" -ForegroundColor Red
        }

        Start-Sleep -Milliseconds 400
    }
}

Write-Host "`n=== Итог ===" -ForegroundColor Yellow
$files = Get-ChildItem $out_dir -Filter "27612_*.txt" -ErrorAction SilentlyContinue
Write-Host "Скачано файлов: $($files.Count)"
$files | Select-Object Name, Length | Format-Table -AutoSize