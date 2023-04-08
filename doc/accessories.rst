.. currentmodule:: emborg

.. _emborg_accessories:

Accessories
===========

.. _borg space:

Borg-Space
----------

`Borg-Space <https://github.com/KenKundert/borg-space>`_ is a utility that 
reports and tracks the space required by your *Borg* repositories.
It also allows you to graph the space used over time.


.. _ntlog accessory:

Logging with ntLog
------------------

`ntLog <https://github.com/KenKundert/ntlog>`_ is a log file aggregation 
utility.

When run *Emborg* writes over a previously generated logfile.  This becomes 
problematic if you have one  cron script that runs *create* frequently and 
another that runs a command like *prune* less frequently. If there is trouble 
with the *prune* command it will be difficult to see and resolve because its 
logfile will be overwritten by subsequent *create* commands.

*ntlog* can be run after each *Emborg* run to aggregate the individual logfile 
from each run into a single accumulating log file.  To arrange this you can use 
:ref:`run_after_borg <run_after_borg>`::

    run_after_borg = 'ntlog --delete --keep-for 7 ~/.local/share/emborg/{config_name}.log'

This accumulates the log files as they are created to 
~/.local/share/emborg/{config_name}.log.nt.



