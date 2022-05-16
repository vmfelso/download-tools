![Interrogate badge](badges/interrogate_badge.svg)
![Coverage badge](badges/coverage.svg)

# download-tools

Tool for downloading experiment data when using a combination of psiturk + jsPsych 

## Installation

To install:

```
git clone https://github.com/RationalityEnhancementGroup/download-tools.git
cd download-tools
pip install -e .
```

You can also install this without directly cloning the git repository:

```
pip install git+https://github.com/RationalityEnhancementGroup/download-tools.git@main#egg=download_tools
```

## How to download psiTurk Files?

## Set up

#### Set Database URIs

In order to download experiments, please add database URIs (e.g. Postgres URIs)
to a local file `.database_uris`:

The format of the file should be each database on one line, with a tab between the name and uri:

```
database_name1	database_uri1
database_name2	database_uri2
```

#### Create HIT ID Files

Next for any experiment you run, enter all the experiment HIT IDs as entries in a text file
named `<EXPERIMENT_NAME>.txt` and save that text file to some local folder, e.g. `hit_ids`.

### Examples

#### Create a labeler to deidentify most data files

If you want to use the same labeler, you should save it into a location and NEVER publish it:

```
from download_tools.labeler import Labeler
import dill as pickle

pid_labeler = Labeler()
pickle.dump(pid_labeler.labels, open("./mturk_id_mapping.pickle", "wb"))
```

#### Get experiment data

```
from download_tools.download_from_database import load_database_uris, download_from_database
from download_tools.save_participant_files import save_participant_files

load_database_uris(".")
example_participant_dicts = download_from_database("./hit_ids/<EXPERIMENT_NAME>.txt", "NEW")

save_participant_files(example_participant_dicts, <EXPERIMENT_NAME>, labeler="./mturk_id_mapping.pickle", save_path=".")

```

The experiment files should now exist in the local folder `data/human/<EXPERIMENT_NAME>/`. There will be a csv file for each
type of jsPsych trial presented to participants.

## Testing

#### Virtual environment

Set up a virtual environment:
````
python3 -m venv env
source env/bin/activate
pip install -e .
````
