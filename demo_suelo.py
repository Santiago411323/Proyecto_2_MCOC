"""5A: fundación IFC con contacto basal efectivo, parámetros didácticos explícitos."""
import argparse
import json
from pathlib import Path
import time
import uuid
from therma.ejecutar import ejecutar


def configuracion(temperatura_suelo=10., malla=0):
    return dict(geometry='foundation', meshIndex=malla, source='none', calibrate=False, days=14.,
        faces=[dict(type='R', temp=20., h=10., R=0., flux=0.) for _ in range(6)],
        construction=dict(model='exponential_adiabatic',
            parameter_source='Hipótesis didácticas: theta_inf=40 C, tau=24 h; sin ensayo de mezcla real.',
            pours=[dict(id=i+1, start_h=24.*i, placement_C=18., theta_inf_C=40., tau_h=24.) for i in range(3)]),
        environment=dict(soil=dict(model='effective_basal_reservoir', temperature_C=temperatura_suelo,
            depth_m=1., conductivity_W_mK=1.5, contact_R_m2K_W=0.,
            parameter_source='Hipótesis didácticas declaradas: Ts configurable, Ls=1 m, ks=1.5 W/(m K), Rc=0; no mediciones de Punta Arenas.')))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--temperatura-suelo', type=float, default=10.)
    parser.add_argument('--malla', type=int, choices=[0,1], default=0)
    parser.add_argument('--factor', type=float, default=.7, help='Fracción de dt crítico; el integrador también limita el paso por hidratación.')
    args=parser.parse_args(); ident=uuid.uuid4().hex
    output=Path(__file__).resolve().parent/'resultados'/'servidor_therma'/ident
    config=configuracion(args.temperatura_suelo,args.malla); config['factor']=args.factor
    start=time.perf_counter(); meta=ejecutar(config,ident,output)
    report=dict(run_id=ident, output=str(output), mesh=meta['geometry'],
        Tmax_C=meta['metrics']['maxField'], peak_h=meta['metrics']['global_peak_time_s']/3600,
        hottest_ijk=meta['metrics']['hottest_xyz'],
        hottest_position_m=[o+(i+.5)*d for o,i,d in zip(meta['geometry']['origin_m'],meta['metrics']['hottest_xyz'],meta['geometry']['spacing_m'])],
        energy_residual_relative=meta['metrics']['energy_residual_relative'],
        soil_into_concrete_MJ=meta['metrics']['final_soil_into_concrete_J']/1e6,
        air_into_concrete_MJ=meta['metrics']['final_air_into_concrete_J']/1e6,
        runtime_solver_s=meta['metrics']['runtime_s'], runtime_total_s=time.perf_counter()-start,
        dt_max_used_s=meta['metrics']['dt'], steps=meta['metrics']['steps'],
        deltaT_25mm=meta['validity']['project_deltaT_25mm'])
    # Geometría completa y máscaras permanecen en metadata.json y campos.npz.
    report['mesh']={k:meta['geometry'][k] for k in ('shape_xyz','spacing_m','origin_m')}
    (output/'resumen_suelo.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(report,indent=2,ensure_ascii=False))


if __name__=='__main__':main()
