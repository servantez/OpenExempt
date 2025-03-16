from dataclasses import dataclass


@dataclass
class Party:
    first_name: str
    last_name: str

    def __str__(self):
        return f'Party(name: {self.full_name()})'
    
    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    def pluralize_last_name(self):
        if self.last_name.endswith(('s', 'x', 'z', 'ch', 'sh')):
            return self.last_name + 'es'
        else:
            return self.last_name + 's'
