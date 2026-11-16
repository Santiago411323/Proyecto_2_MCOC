# Exploración constructiva S25 IFC

104 casos; 100 cálculos nuevos, 4 reutilizados. Un clima, cuatro fuentes SS provisionales. P_T, P_Delta y P_f: INDETERMINADAS.

## exploracion_constructiva

| Plan | D_h | Tmax_worst_C | Delta_S25_est_worst_C | coverage_air_min_percent | all_horizons_captured | compliance |
|---|---|---|---|---|---|---|
| Una vertida continua | 24.353 | 55.084 | 39.902 | 100.000 | True | INDETERMINADO |
| Espera 0 h | 24.353 | 55.084 | 39.902 | 100.000 | True | INDETERMINADO |
| Tres piezas sin espera, Tcol12, EPS25 | 24.353 | 50.219 | 27.428 | 100.000 | False | INDETERMINADO |
| Más rápido | 34.115 | 54.593 | 39.533 | 100.000 | True | INDETERMINADO |
| Dos operaciones, espera 12 h | 36.353 | 54.337 | 39.403 | 100.000 | True | INDETERMINADO |
| Espera 6 h | 36.353 | 54.816 | 39.704 | 100.000 | True | INDETERMINADO |
| Intervalo 18 h | 38.115 | 54.484 | 39.527 | 100.000 | True | INDETERMINADO |
| Espera 12 h | 48.353 | 54.291 | 39.582 | 100.000 | True | INDETERMINADO |
| Propuesto | 50.115 | 53.950 | 39.385 | 100.000 | True | INDETERMINADO |
| Propuesto Tcol 12 C | 50.115 | 48.755 | 34.821 | 100.000 | True | INDETERMINADO |
| Propuesto Tcol 24 C | 50.115 | 59.159 | 43.949 | 100.000 | True | INDETERMINADO |
| Propuesto sin moldaje | 50.115 | 53.949 | 41.399 | 100.000 | True | INDETERMINADO |
| Propuesto EPS 25 mm | 50.115 | 55.303 | 31.474 | 100.000 | False | INDETERMINADO |
| Propuesto EPS 50 mm | 50.115 | 55.882 | 28.188 | 100.000 | False | INDETERMINADO |
| Propuesto retiro moldaje 72 h | 50.115 | 53.950 | 41.351 | 100.000 | True | INDETERMINADO |
| Espera 18 h | 60.353 | 53.799 | 39.443 | 100.000 | True | INDETERMINADO |
| Espera 24 h | 72.353 | 53.132 | 39.126 | 100.000 | True | INDETERMINADO |
| Intervalo 36 h | 74.115 | 52.993 | 38.901 | 100.000 | True | INDETERMINADO |
| Espera 36 h | 96.353 | 51.957 | 38.273 | 100.000 | True | INDETERMINADO |
| Más lento | 98.115 | 52.020 | 38.016 | 100.000 | True | INDETERMINADO |
## exploracion_refinada

| Plan | D_h | Tmax_worst_C | Delta_S25_est_worst_C | coverage_air_min_percent | all_horizons_captured | compliance |
|---|---|---|---|---|---|---|
| Una vertida continua | 24.353 | 54.929 | 40.250 | 92.939 | True | INDETERMINADO |
| Tres piezas sin espera, Tcol12, EPS25 | 24.353 | 50.379 | 27.628 | 92.939 | True | INDETERMINADO |
| Sin espera, Tcol12, sin EPS | 24.353 | 49.563 | 35.623 | 92.939 | True | INDETERMINADO |
| Propuesto | 50.115 | 53.384 | 39.654 | 92.939 | True | INDETERMINADO |
| Propuesto Tcol 12 C | 50.115 | 48.437 | 35.235 | 92.939 | True | INDETERMINADO |
## exploracion_eps50_refinada

| Plan | D_h | Tmax_worst_C | Delta_S25_est_worst_C | coverage_air_min_percent | all_horizons_captured | compliance |
|---|---|---|---|---|---|---|
| Propuesto EPS 50 mm | 50.115 | 56.677 | 28.754 | 92.939 | False | INDETERMINADO |

Máximos descriptivos entre cuatro curvas completas; no son probabilidades. S25 no validado, cobertura parcial en malla fina. Las advertencias de horizonte indican picos tardíos o aún crecientes; no se extiende con clima inventado.

## Abrir campos calculados en THERMA

- [Una vertida continua · 500 mm · M4_SS](http://127.0.0.1:8767/panel_termico.html?result=29c7d22b2371df692e1c988c95d8e005)
- [Espera 0 h · 500 mm · M4_SS](http://127.0.0.1:8767/panel_termico.html?result=29c7d22b2371df692e1c988c95d8e005)
- [Tres piezas sin espera, Tcol12, EPS25 · 500 mm · M4_SS](http://127.0.0.1:8767/panel_termico.html?result=314075e86868bd184e28c92f0ad0b251)
- [Más rápido · 500 mm · M4_SS](http://127.0.0.1:8767/panel_termico.html?result=1119f13cc975cb714842ed9f4b5753c1)
- [Dos operaciones, espera 12 h · 500 mm · M4_SS](http://127.0.0.1:8767/panel_termico.html?result=e5c2ea6a4d68976b9361ec96c2467fe6)
- [Espera 6 h · 500 mm · M4_SS](http://127.0.0.1:8767/panel_termico.html?result=23e772537fccb9607005205106b208db)
- [Intervalo 18 h · 500 mm · M4_SS](http://127.0.0.1:8767/panel_termico.html?result=00f204c67ff561a2bc5ffbd3c2b17dee)
- [Espera 12 h · 500 mm · M4_SS](http://127.0.0.1:8767/panel_termico.html?result=125969a053949a57db6f5c3edd2110bd)
- [Propuesto · 500 mm · M4_SS](http://127.0.0.1:8767/panel_termico.html?result=96b6d88d3e1fea2645db5585966c1604)
- [Propuesto Tcol 12 C · 500 mm · M4_SS](http://127.0.0.1:8767/panel_termico.html?result=0653a252d230def79ccc22a46f5f2d73)
- [Propuesto Tcol 24 C · 500 mm · M4_SS](http://127.0.0.1:8767/panel_termico.html?result=80cbdf2083e70859a5fe96d366c72356)
- [Propuesto sin moldaje · 500 mm · M4_SS](http://127.0.0.1:8767/panel_termico.html?result=f09c4877b9a273683d5dc0d852faa365)
- [Propuesto EPS 25 mm · 500 mm · M4_SS](http://127.0.0.1:8767/panel_termico.html?result=35d106f6207a3980fb079f85f9b284e1)
- [Propuesto EPS 50 mm · 500 mm · M4_SS](http://127.0.0.1:8767/panel_termico.html?result=e8b1368c697291dbf7794321f9bf3249)
- [Propuesto retiro moldaje 72 h · 500 mm · M4_SS](http://127.0.0.1:8767/panel_termico.html?result=11eefab380b2bc834fbd1204ca586acf)
- [Espera 18 h · 500 mm · M4_SS](http://127.0.0.1:8767/panel_termico.html?result=082e31ec338015389dcee010b8a7578c)
- [Espera 24 h · 500 mm · M4_SS](http://127.0.0.1:8767/panel_termico.html?result=eaadbb6ced1767bd73c721e85f198129)
- [Intervalo 36 h · 500 mm · M4_SS](http://127.0.0.1:8767/panel_termico.html?result=a61c609330b442bc4bdfa3017af45765)
- [Espera 36 h · 500 mm · M4_SS](http://127.0.0.1:8767/panel_termico.html?result=a69e420cc4879a62a39d65451b80f177)
- [Más lento · 500 mm · M4_SS](http://127.0.0.1:8767/panel_termico.html?result=2751bf2a68612722729294cb4c1411db)
- [Una vertida continua · 250 mm · M4_SS](http://127.0.0.1:8767/panel_termico.html?result=8f419e09c1bb6df927acafed24d7f22a)
- [Tres piezas sin espera, Tcol12, EPS25 · 250 mm · M4_SS](http://127.0.0.1:8767/panel_termico.html?result=fb691ceb68a365d6f715abf0ae313bac)
- [Sin espera, Tcol12, sin EPS · 250 mm · M4_SS](http://127.0.0.1:8767/panel_termico.html?result=7755595229cbcd9e4fdf6ac6e26be64f)
- [Propuesto · 250 mm · M4_SS](http://127.0.0.1:8767/panel_termico.html?result=4c456e3167f42ba1b5d88f9e8f23b7bc)
- [Propuesto Tcol 12 C · 250 mm · M4_SS](http://127.0.0.1:8767/panel_termico.html?result=0997a6c5b56a4b40b403e1fff4791e93)
- [Propuesto EPS 50 mm · 250 mm · M4_SS](http://127.0.0.1:8767/panel_termico.html?result=822808ef6bb1d58c4e97279b566cf2c9)