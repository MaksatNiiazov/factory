from typing import Optional

from catalog.models import SSGCatalog
from ops.services.base_selection import BaseSelectionAvailableOptions


class SpacerSelectionAvailableOptions(BaseSelectionAvailableOptions):
    """Подбор распорок SSG"""

    @classmethod
    def get_default_params(cls):
        return {
            'load_and_move': {
                'installation_length': None,
                'load': None,
                'load_type': None,
                'mounting_length': 0,
            },
            'pipe_options': {
                'location': None,
                'spacer_counts': None,
            },
            'variant': None,
        }

    def get_installation_length(self) -> Optional[int]:
        return self.params['load_and_move']['installation_length']

    def get_mounting_length(self) -> int:
        return self.params['load_and_move'].get('mounting_length') or 0

    def get_load_type(self) -> Optional[str]:
        return self.params['load_and_move']['load_type']

    def get_spacer_counts(self) -> Optional[int]:
        return self.params['pipe_options']['spacer_counts']

    def get_pipe_location(self) -> Optional[str]:
        return self.params['pipe_options']['location']

    def get_available_pipe_locations(self):
        return ['horizontal', 'vertical']

    def get_available_spacer_counts(self):
        location = self.get_pipe_location()
        if location == 'vertical':
            return [2]
        elif location == 'horizontal':
            return [1, 2]
        return []

    def get_load(self) -> Optional[float]:
        load_type = self.get_load_type()
        load = self.params['load_and_move']['load']
        if load_type is None or load is None:
            self.debug.append('Не указана нагрузка или её тип')
            return None

        if load_type == 'hz':
            load /= 1.5
        elif load_type == 'hs':
            load /= 1.7

        counts = self.get_spacer_counts()
        if counts and counts > 1:
            load /= counts
        return load

    def get_suitable_entry(self) -> Optional[SSGCatalog]:
        load = self.get_load()
        if load is None:
            return None
        installation_length = self.get_installation_length()
        mount_len = self.get_mounting_length()
        candidates = (
            SSGCatalog.objects.filter(fn__gte=load)
            .order_by('fn', 'l_min')
        )

        by_fn = {}
        for c in candidates:
            by_fn.setdefault(c.fn, []).append(c)

        for fn in sorted(by_fn.keys()):
            ranges = by_fn[fn]
            if installation_length is None:
                return ranges[0]

            block_length = installation_length - mount_len
            for idx, r in enumerate(ranges):
                if r.l_min <= block_length <= r.l_max:
                    return r
        return None

    def get_available_options(self):
        options = {
            'pipe_options': {
                'locations': self.get_available_pipe_locations(),
                'spacer_counts': self.get_available_spacer_counts(),
            },
            'suitable_entry': None,
            'debug': self.debug,
        }
        entry = self.get_suitable_entry()
        if entry:
            installation_length = self.get_installation_length()
            mount_len = self.get_mounting_length()
            same_fn = list(
                SSGCatalog.objects.filter(fn=entry.fn).order_by('l_min')
            )
            type_val = 1 if same_fn and same_fn[0].id == entry.id else 2

            if installation_length is None:
                block_length = entry.l_min
                final_length = block_length + mount_len
            else:
                block_length = installation_length - mount_len
                final_length = installation_length

            options['suitable_entry'] = {
                'id': entry.id,
                'marking': f'SSG {entry.fn:04d}.{int(final_length):04d}.{type_val}',
                'fn': entry.fn,
                'block_length': int(block_length),
                'final_length': int(final_length),
                'type': type_val,
            }
        return options