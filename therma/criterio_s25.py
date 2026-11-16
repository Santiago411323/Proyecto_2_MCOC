"""Decisión asimétrica: un testigo validado basta para excedencia, no para aprobación."""
import math
from decimal import Decimal


def evaluar_testigos(witnesses,full_surface_coverage=False,global_delta_upper_bound_C=None,global_bound_validated=False,threshold=20.):
    validated=[];exceeds=False
    for w in witnesses:
        if not w.get('validated') or w.get('error_bound_C') is None:continue
        value=w['delta_C'];error=w['error_bound_C']
        if not all(isinstance(x,(int,float)) and math.isfinite(x) for x in (value,error)) or error<0:
            raise ValueError('Diferencial y cota de error finitos; cota no negativa.')
        validated.append(dict(id=w.get('id'),lower_C=value-error,upper_C=value+error))
        exceeds |= Decimal(str(value))-Decimal(str(error))>Decimal(str(threshold))
    if exceeds:
        return dict(status='EXCEEDS_VALIDATED_WITNESS',I_Delta=True,can_prove_exceedance=True,can_exclude_exceedance=False,validated_intervals=validated)
    # Una cota del máximo global debe incluir puntos ausentes, tiempo y error de borde.
    if full_surface_coverage and global_bound_validated and global_delta_upper_bound_C is not None:
        value=global_delta_upper_bound_C
        if not isinstance(value,(int,float)) or not math.isfinite(value):raise ValueError('Cota superior global finita.')
        if value<=threshold:
            return dict(status='COMPLIES_VALIDATED_GLOBAL_BOUND',I_Delta=False,can_prove_exceedance=False,can_exclude_exceedance=True,validated_intervals=validated)
    return dict(status='INDETERMINATE',I_Delta=None,can_prove_exceedance=False,can_exclude_exceedance=False,
                reason='No hay testigo con cota validada que exceda, ni cota superior global validada.',validated_intervals=validated)
