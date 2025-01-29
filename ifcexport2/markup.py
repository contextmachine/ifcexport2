import dataclasses

import rich


@dataclasses.dataclass
class ProgressBarStyle:
    completed_color:str='blue'
    uncompleted_color: str='grey'
    completed_symbol: str="█"
    uncompleted_symbol: str="░"
class ProgressBar:
    """
    >>> import time
    >>> pb=ProgressBar(60,20)
    >>> next(pb)

    >>> for i in range(20):
    >>>     time.sleep(1)
    >>>     next(pb)
  ██████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 6/20               # example at six iteration
    """
    def __init__(self, size:int=80, steps_count:int=4, style:ProgressBarStyle=None,fl=None, **kwargs):
        if style is None:
            style=ProgressBarStyle()
        self.console=rich.get_console()
        self.size=size
        self.steps_count=steps_count
        self.fl=fl
        self.current_step=0
        self.style=style
        self.step_size=size//steps_count

    def print_progress(self):
        rich.print(
            f"  " + f"[{self.style.completed_color}]" + self.style.completed_symbol *self.current_step*self.step_size + f"[/{self.style.completed_color}]"+ f"[{self.style.uncompleted_color}]" + (self.style.uncompleted_symbol * (self.size-self.current_step*self.step_size)) + f"[/{self.style.uncompleted_color}]" + f" [{self.style.completed_color}][bold]{self.current_step}/{self.steps_count}[/bold][/{self.style.completed_color}]",
            end='\r',flush=True,file=self.fl)
    def __next__(self):
        if self.current_step>self.steps_count:

            raise StopIteration
        self.print_progress()
        self.current_step+=1




    def print_rgb(self, text:str, r:int,g:int,b:int):
        self.console.print(text.format(**self.__dict__), style=f"rgb({r},{g},{b})")
