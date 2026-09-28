# צילומי מסך

| קובץ | דף | מצב |
|---|---|---|
| `map.png` | `web/map.html` | המפה המלאה, בלי סימון |
| `diagnostic_static.png` | `web/diagnostic_static.html#demo` | סיום המבחן הסטטי: תלמיד שלא יודע al7 |
| `diagnostic_adaptive.png` | `web/diagnostic_adaptive.html#demo` | סיום האבחון האדפטיבי: תלמיד שלא יודע ar4 |
| `journey_stage1.png` | `web/journey.html` | שלב 1 של המסע – שאלת הבגרות |
| `guided.png` | `web/guided.html#section=ד` | סולם שאלות מנחות לסעיף ד׳ – תצוגת תלמיד |
| `guided_teacher.png` | `web/guided.html#section=ד&teacher=1` | אותו סולם – תצוגת מורה |
| `journey.png` | `web/journey.html#demo` | סיום המסע: תלמיד שלא יודע ca4 |

**איך לצלם מחדש:** `make screenshots` (או `docs/screenshots/capture.sh`). הסקריפט משתמש ב־Chrome, Chromium או Edge במצב headless, ולא מוסיף תלויות לפרויקט. דפדפן במיקום אחר: `BROWSER=/path/to/chrome make screenshots`. בלי דפדפן כזה: פותחים כל דף (עם `#demo` לדפים 2–4, ועם `#section=ד` לדף 5) ומצלמים ביד ברוחב 1440px.
