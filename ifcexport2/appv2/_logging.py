import logging
FMT_WITH_FP = "%(levelname)s:    %(message)s %(pathname)s:%(lineno)s"


level='levelname'
message='message'
path='pathname'
time='asctime'
line='line'

class ColourFormatter(logging.Formatter):
    """Add ANSI colour codes based on record.levelno."""
    COLOURS = {
        logging.DEBUG:    "\033[36m",      # cyan
        logging.INFO:     "\033[32m",      # green
        logging.WARNING:  "\033[33m",      # yellow
        logging.ERROR:    "\033[31m",      # red
        logging.CRITICAL: "\033[41m",      # red background
        'pathname':"\033[90m"
    }
    
    RESET = "\033[0m"

    # note the rich format string — add anything you like here%(asctime)s %(levelname)s: %(message)s
    BASE_FMT = "%(asctime)s %(levelname)s: %(message)s"
    FMT_WITH_FP = f"%(levelname)s:    %(message)s %(pathname)s:%(lineno)d"
    
    def __init__(self, fmt=None, datefmt=None, style='%', validate=True, *,
                 defaults=None, ):
        if fmt is None:
            fmt=self.__class__.BASE_FMT
        super().__init__(fmt=fmt, datefmt=datefmt,style=style,validate=validate,defaults=defaults)
        self.fmt=fmt
    def format(self, record):
        
        colour = self.COLOURS.get(record.levelno, self.RESET)
        record.levelname = f"{colour}{record.levelname}{self.RESET}"
        if record.pathname :
            record.pathname=f'{self.COLOURS.get("pathname")}{record.pathname}'
         
            
            
            
        # You may also colour the whole line:  return f"{colour}{line}{self.RESET}"
        return super().format(record)