# my_project/main.py
import json
import math
import re
import time
from bisect import bisect_right
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from pprint import pprint
from typing import Any, Callable, Optional

from pynput.keyboard import Key

import autosynergism.ocr
from autosynergism.action import Actions
from autosynergism.geometry import Geometry


def reduce_fraction(numerator, denominator):
    fraction = Fraction(numerator, denominator)
    return fraction.numerator, fraction.denominator


HAS_ASCENDED = False
TIME_TO_LUCK = 0
AMBROSIA_LOADOUT = None

STATE = {
    "CURRENT_TAB": "",
    "TIME_TO_LUCK": 0,
    "AMBROSIA_LOADOUT": "",
    "HIGHEST_BEATEN_CHALLENGE": 8,
    "SINGS": 0,
    "P4x4": 0,
    "GQ_SPENT": 0,
    "QUARKS_SPENT": 0,
    "GQ_PER_HOUR": 0,
    "QUARKS_PER_HOUR": 0,
    "GQ_SPENT_LAST_SING": 0,
    "QUARKS_SPENT_LAST_SING": 0,
    "TIME_TO_SING": 0,
    "SING_STARTED_AT": 0,
}


# challenge_string
def c(highest=None):
    h = STATE["HIGHEST_BEATEN_CHALLENGE"] if highest is None else highest
    if h < 10:
        return ":C9"
    elif h < 11:
        return ":C10"
    return ""


@dataclass
class AmbrosiaUpgrade:
    name: str
    cost: Callable[[int], float]
    blue_berry_cost: int = 0
    max_level: int = 1

    cubes: Callable[[int, int], float] | Callable[[int], float] = field(
        default_factory=lambda: lambda _: 1
    )
    quarks: Callable[[int, int], float] | Callable[[int], float] = field(
        default_factory=lambda: lambda _: 1
    )
    luck: Callable[[int, int], float] | Callable[[int], float] = field(
        default_factory=lambda: lambda _: 0
    )

    def cumulative_cost(self, stop=None, start=None):
        if start is None:
            start = 0
        if stop is None:
            stop = self.max_level
        start, stop = min(start, stop), max(start, stop)
        return sum(self.cost(level) for level in range(start, stop + 1))


def delete_old_files(folder_path, filename_prefix, dry_run=True):
    folder = Path(folder_path)

    files = list(folder.glob(f"{filename_prefix}*"))

    if not files:
        if not dry_run:
            print(f"Files to be deleted:")
        return

    # Sort files by last modification time (newest first)
    files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

    newest_file, *old_files = files

    if not dry_run:
        deleted_files = []
        not_deleted_files = []
        for file in old_files:
            try:
                file.unlink()
                deleted_files.append(f"{file}")
            except Exception as e:
                not_deleted_files.append(f"{file}: {e}")
                pass
        print("Deleted file:\n    ", "\n    ".join(str(x) for x in deleted_files))
        print(
            f"Failed to delete:\n    " "\n    ".join(str(x) for x in not_deleted_files)
        )
    else:
        print(f"Files to be deleted:\n   ", "\n    ".join(str(x) for x in old_files))
    return newest_file


def load_stats():
    newest_file = delete_old_files(
        Path.home() / "Downloads", "Statistics-Synergism", True
    )
    if newest_file is None:
        return {}
    stats = {"ooms": 0.0}
    with open(newest_file) as f:
        for line in f.readlines():
            line = line.lower().strip()
            if ":" not in line:
                continue
            name, content = [x.strip() for x in line.split(":", maxsplit=1)]
            if name == "quarks":
                stats["quarks"] = float(content)
            elif name == "golden quarks":
                stats["golden quarks"] = float(content)
            elif line.startswith("wow"):
                cubes = None
                try:
                    cubes = float(content)
                except ValueError:
                    cubes = float(content.split(maxsplit=1)[0])
                oom = math.floor(math.log10(cubes + 1) + 1)
                stats["ooms"] += oom
            elif "quark hepteract" == name:
                current, maximum = [float(x) for x in content.split("/", maxsplit=1)]
                stats["quark_hepteract"] = current
                stats["quark_hepteract_max"] = 2 * maximum
        STATE["STATS"] = stats
    return stats


def base_cost_formula(level: int, base: float, power: int = 3):
    return base * (level**power - (max(level - 1, 0)) ** power)


{
    "ambrosiaTutorial": 10,
    "ambrosiaPatreon": 1,
    "ambrosiaHyperflux": 5,
    "ambrosiaQuarks1": 20,
    "ambrosiaCubes1": 50,
    "ambrosiaLuck1": 20,
    "ambrosiaLuckCube1": 7,
    "ambrosiaQuarkCube1": 7,
    "ambrosiaCubes2": 15,
}


@dataclass
class Ambrosia:
    quarks: float = 0
    ooom: int = 0

    def __post_init__(self):
        pass

        amb = {}
        ####==========###
        # LEVEL 1     ###
        ####===========##
        amb["ambrosiaTutorial"] = AmbrosiaUpgrade(
            name="Ambrosia Tutorial Module",
            cost=lambda n: base_cost_formula(level=n, base=1, power=2),
            cubes=lambda n: 1 + 0.05 * n,
            quarks=lambda n: 1 + 0.01 * n,
            max_level=10,
        )
        amb["ambrosiaPatreon"] = AmbrosiaUpgrade(
            name="Shameless, Ambrosial Patreon Reminder",
            cost=lambda _: float(1),
            max_level=1,
        )
        amb["ambrosiaHyperflux"] = AmbrosiaUpgrade(
            name="Shameless, Ambrosial Patreon Reminder",
            cost=lambda x: 33333 + 33333 * min(4, x - 1) * max(1, 3 ** (x - 5)),
            cubes=lambda n, y: (1 + (1 / 100) * n) ** y,
            max_level=7,
        )
        amb["obtainium"] = AmbrosiaUpgrade(
            name="RNG-based Obtainium Booster",
            cost=lambda x: 500 * 25 ** (x - 1),
            max_level=2,
        )
        amb["offerings"] = AmbrosiaUpgrade(
            name="RNG-based Offering Booster",
            cost=lambda x: 500 * 25 ** (x - 1),
            max_level=2,
        )
        ####==========###
        # LEVEL 2     ###
        ####===========##
        amb["ambrosiaQuarks1"] = AmbrosiaUpgrade(
            name="Ambrosia Quark Module I",
            cost=lambda x: base_cost_formula(level=x, base=1, power=3),
            quarks=lambda n: 1 + 0.01 * n,
            max_level=100,
        )
        amb["ambrosiaCubes1"] = AmbrosiaUpgrade(
            name="Ambrosia Cube Module I",
            cost=lambda x: base_cost_formula(level=x, base=1, power=3),
            cubes=lambda x: (1 + 0.05 * x) * math.pow(1.1, math.floor(x / 10)),
            max_level=100,
        )
        amb["ambrosiaLuck1"] = AmbrosiaUpgrade(
            name="Ambrosia Luck Module I",
            cost=lambda x: base_cost_formula(level=x, base=1, power=3),
            luck=lambda x: 2 * x + 12 * int(x / 10),
            max_level=100,
        )
        ####==========###
        # LEVEL 3     ###
        ####===========##
        amb["ambrosiaCubeQuark1"] = AmbrosiaUpgrade(
            name="Ambrosia Cube-Quark Hybrid Module I",
            cost=lambda x: base_cost_formula(level=x, base=500, power=3),
            quarks=lambda n, y: 1 + 0.0001 * n * y,
            max_level=25,
        )
        amb["ambrosiaLuckQuark1"] = AmbrosiaUpgrade(
            name="Ambrosia Cube-Quark Hybrid Module I",
            cost=lambda x: base_cost_formula(level=x, base=500, power=3),
            quarks=lambda n, y: 1 + 0.0001 * n * min(y, 1000**0.5 * y**0.5),
            max_level=25,
        )
        amb["ambrosiaLuckCube1"] = AmbrosiaUpgrade(
            name="Ambrosia Quark-Cube Hybrid Module I",
            cost=lambda x: base_cost_formula(level=x, base=250, power=3),
            cubes=lambda n, y: 1 + 0.0002 * n * y,
            max_level=25,
        )
        amb["ambrosiaQuarkCube1"] = AmbrosiaUpgrade(
            name="Ambrosia Quark-Cube Hybrid Module I",
            cost=lambda x: base_cost_formula(level=x, base=250, power=3),
            cubes=lambda n, y: 1
            + (0.0005 * n * math.floor((math.log10(y + 1) + 1) ** 2)),
            max_level=25,
        )
        amb["ambrosiaCubeLuck1"] = AmbrosiaUpgrade(
            name="Ambrosia Cube-Luck Hybrid Module I",
            cost=lambda x: base_cost_formula(level=x, base=100, power=3),
            luck=lambda n, y: 0.02 * n * y,
            max_level=25,
        )
        amb["ambrosiaQuarkLuck1"] = AmbrosiaUpgrade(
            name="Ambrosia Quark-Cube Hybrid Module I",
            cost=lambda x: base_cost_formula(level=x, base=100, power=3),
            luck=lambda n, y: 0.02 * n * math.floor((math.log10(y + 1) + 1) ** 2),
            max_level=25,
        )
        ####==========###
        # LEVEL 4     ###
        ####===========##
        amb["ambrosiaQuarks2"] = AmbrosiaUpgrade(
            name="Ambrosia Quark Module II",
            cost=lambda x: base_cost_formula(level=x, base=500, power=2),
            quarks=lambda n, y: 1 + (0.01 + (y // 10) / 1000) * n,
            max_level=100,
        )
        amb["ambrosiaCubes2"] = AmbrosiaUpgrade(
            name="Ambrosia Cube Module II",
            cost=lambda x: base_cost_formula(level=x, base=500, power=2),
            cubes=lambda n, y: (1 + (0.06 + 6 * (math.floor(y / 10) / 1000)) * n)
            * math.pow(1.13, math.floor(n / 10)),
            max_level=100,
        )
        amb["ambrosiaLuck2"] = AmbrosiaUpgrade(
            name="Ambrosia Luck Module II",
            cost=lambda x: base_cost_formula(level=x, base=250, power=2),
            luck=lambda n, y: (3 + 0.3 * (y // 10)) * n + 40 * (n // 10),
            max_level=100,
        )
        self._ambrosia_upgrades = amb

        cumulative_cost = {}
        for name, upgrade in self._ambrosia_upgrades.items():
            cumulative_cost[name] = {}
            for elem in range(upgrade.max_level + 1):
                cumulative_cost[name][elem] = upgrade.cumulative_cost(
                    elem
                )  # Fixed spelling
            for i in [1, 2]:
                cumulative_cost[name][upgrade.max_level + i] = cumulative_cost[name][
                    upgrade.max_level + i - 1
                ]
            cumulative_cost[name][-1] = 0

        self.cumulative_cost = cumulative_cost

    def recursive_yield(
        self,
        ambrosia,
        levels,
        ranges=None,
        upgrades=None,
        pre_boughts=None,
        luck_restrictor=None,
    ):
        if upgrades is None:
            upgrades = {}
            if pre_boughts:
                upgrades = dict(pre_boughts)
                spent_on_preboughts = sum(
                    self.cumulative_cost[name][level]
                    for name, level in upgrades.items()
                )
                ambrosia -= spent_on_preboughts

        if ranges is None:
            ranges = {}
            for level in levels:
                start = 0
                stop = self._ambrosia_upgrades[level].max_level
                if pre_boughts is not None and level in pre_boughts:
                    start = pre_boughts[level]
                ranges[level] = [i for i in range(start, stop + 1)]
                if level == "ambrosiaTutorial":
                    if pre_boughts and level in pre_boughts:
                        ranges[level] = [pre_boughts[level]]
                    elif ambrosia > 100:
                        ranges[level] = [
                            self._ambrosia_upgrades["ambrosiaTutorial"].max_level
                        ]

        if not levels:
            if ambrosia >= 0:
                yield dict(upgrades)
            return

        name = levels[0]
        previous_level = upgrades.get(name, 0)

        dependencies_met = True
        for level in ranges[name]:
            new_upgrades = dict(upgrades)
            new_upgrades[name] = level

            # Check dependencies
            if (
                name == "ambrosiaQuarks1"
                and new_upgrades.get("ambrosiaTutorial", 0) < 10
            ):
                dependencies_met = False
            elif (
                name == "ambrosiaCubes1"
                and new_upgrades.get("ambrosiaTutorial", 0) < 10
            ):
                dependencies_met = False
            elif (
                name == "ambrosiaLuck1" and new_upgrades.get("ambrosiaTutorial", 0) < 10
            ):
                dependencies_met = False
            elif (
                name == "ambrosiaLuck1"
                and luck_restrictor
                and level > new_upgrades.get(luck_restrictor, 0) + 20
            ):
                dependencies_met = False
            elif name == "ambrosiaCubeQuark1" and (
                new_upgrades.get("ambrosiaQuarks1", 0) < 30
                or new_upgrades.get("ambrosiaCubes1", 0) < 20
            ):
                dependencies_met = False
            elif name == "ambrosiaLuckQuark1" and (
                new_upgrades.get("ambrosiaQuarks1", 0) < 30
                or new_upgrades.get("ambrosiaLuck1", 0) < 20
            ):
                dependencies_met = False
            elif name == "ambrosiaLuckCube1" and (
                new_upgrades.get("ambrosiaCubes1", 0) < 30
                or new_upgrades.get("ambrosiaLuck1", 0) < 20
            ):
                dependencies_met = False
            elif name == "ambrosiaQuarkCube1" and (
                new_upgrades.get("ambrosiaCubes1", 0) < 30
                or new_upgrades.get("ambrosiaQuarks1", 0) < 20
            ):
                dependencies_met = False
            elif (
                name == "ambrosiaQuarks2"
                and new_upgrades.get("ambrosiaQuarks1", 0) < 40
            ):
                dependencies_met = False
            elif (
                name == "ambrosiaCubes2" and new_upgrades.get("ambrosiaCubes1", 0) < 40
            ):
                dependencies_met = False
            elif name == "ambrosiaLuck2" and new_upgrades.get("ambrosiaLuck1", 0) < 40:
                dependencies_met = False
            if not dependencies_met and level > 0:
                break

            new_ambrosia = ambrosia
            new_ambrosia -= self.cumulative_cost[name][level]
            new_ambrosia += self.cumulative_cost[name][previous_level]

            if new_ambrosia < 0:
                break
            yield from self.recursive_yield(
                ambrosia=new_ambrosia,
                levels=levels[1:],
                upgrades=new_upgrades,
                ranges=ranges,
                luck_restrictor=luck_restrictor,
            )

    def get_upgrade(self, name):
        return self._ambrosia_upgrades.get(name, None)

    def calculate_preboughts_for_quarks(self, ambrosia):

        pre_bought = {}
        tutorial = self._ambrosia_upgrades["ambrosiaTutorial"]
        remaining_ambro = ambrosia

        tutorial_cost = 0
        for level in range(0, tutorial.max_level + 1):
            tutorial_cost = tutorial.cumulative_cost(level)
            if tutorial_cost <= remaining_ambro:
                pre_bought["ambrosiaTutorial"] = level
        remaining_ambro -= tutorial_cost

        if not remaining_ambro:
            return pre_bought
        if remaining_ambro >= 100_000:
            pre_bought["ambrosiaLuck1"] = 20
            pre_bought["ambrosiaCubes1"] = 20
            pre_bought["ambrosiaQuarks1"] = 30
        if remaining_ambro >= 200_000:
            pre_bought["ambrosiaQuarks1"] = 40
            # pre_bought["ambrosiaQuarks2"] = 10
        return pre_bought

    def calculate_preboughts_for_cubes(self, ambrosia):

        pre_bought = {}
        tutorial = self._ambrosia_upgrades["ambrosiaTutorial"]
        remaining_ambro = ambrosia

        tutorial_cost = 0
        for level in range(0, tutorial.max_level + 1):
            tutorial_cost = tutorial.cumulative_cost(level)
            if tutorial_cost <= remaining_ambro:
                pre_bought["ambrosiaTutorial"] = level
        remaining_ambro -= tutorial_cost

        if not remaining_ambro:
            return pre_bought
        if remaining_ambro >= 100_000:
            pre_bought["ambrosiaLuck1"] = 20
            pre_bought["ambrosiaCubes1"] = 30
            pre_bought["ambrosiaQuarks1"] = 20
        if remaining_ambro >= 200_000:
            pre_bought["ambrosiaCubes1"] = 40
            pre_bought["ambrosiaCubes2"] = 10
        if remaining_ambro >= 250_000:
            pre_bought["ambrosiaHyperflux"] = 1
        if remaining_ambro >= 300_000:
            pass
        if remaining_ambro >= 400_000:
            pre_bought["ambrosiaHyperflux"] = 2
        if remaining_ambro >= 500_000:
            pre_bought["ambrosiaCubes1"] = 50
        if remaining_ambro >= 600_000:
            pre_bought["ambrosiaHyperflux"] = 3
        if remaining_ambro >= 1_000_000:
            pre_bought["ambrosiaHyperflux"] = 4
            pre_bought["ambrosiaCubes1"] = 50
        if remaining_ambro >= 1_400_000:
            pre_bought["ambrosiaCubes1"] = 60
        if remaining_ambro >= 1_800_000:
            pre_bought["ambrosiaCubes1"] = 70
        if remaining_ambro >= 2_000_000:
            pre_bought["ambrosiaHyperflux"] = 5
        if remaining_ambro >= 2_500_000:
            pre_bought["ambrosiaCubes1"] = 80
        if remaining_ambro >= 2_800_000:
            pre_bought["ambrosiaCubes2"] = 30
        if remaining_ambro >= 3_100_000:
            pre_bought["ambrosiaCubes1"] = 90
        return pre_bought

    def calculate_preboughts_for_luck(self, ambrosia):

        pre_bought = {}
        tutorial = self._ambrosia_upgrades["ambrosiaTutorial"]
        remaining_ambro = ambrosia

        tutorial_cost = 0
        for level in range(0, tutorial.max_level + 1):
            tutorial_cost = tutorial.cumulative_cost(level)
            if tutorial_cost <= remaining_ambro:
                pre_bought["ambrosiaTutorial"] = level
        remaining_ambro -= tutorial_cost

        if not remaining_ambro:
            return pre_bought
        if remaining_ambro >= 100_000:
            pre_bought["ambrosiaLuck1"] = 30
            pre_bought["ambrosiaCubes1"] = 20
            pre_bought["ambrosiaQuarks1"] = 20
        if remaining_ambro >= 200_000:
            pre_bought["ambrosiaLuck1"] = 40
            # pre_bought["ambrosiaQuarks2"] = 10
        return pre_bought

    def calculate(
        self,
        loadout,
        ambrosia,
        quarks,
        luck_base,
        luck_mult,
        ooms,
        p4x4=40,
        use_preboughts=True,
    ):

        best_loadout = {}
        pre_boughts = None
        if loadout == "quarks":
            if use_preboughts:
                pre_boughts = self.calculate_preboughts_for_quarks(ambrosia)
            best_loadout = self.best_quark_loadout_exact(
                ambrosia=ambrosia,
                pre_boughts=pre_boughts,
                luck_base=luck_base,
                luck_mult=luck_mult,
                ooms=ooms,
            )
        elif loadout == "cubes":
            if use_preboughts:
                pre_boughts = self.calculate_preboughts_for_cubes(ambrosia)
            best_loadout = self.best_cube_loadout_exact(
                ambrosia=ambrosia,
                pre_boughts=pre_boughts,
                luck_base=luck_base,
                luck_mult=luck_mult,
                quarks=quarks,
                p4x4=p4x4,
            )
        elif loadout == "luck":
            if use_preboughts:
                pre_boughts = self.calculate_preboughts_for_luck(ambrosia)
            best_loadout = self.best_luck_loadout_exact(
                ambrosia=ambrosia,
                pre_boughts=pre_boughts,
                luck_base=luck_base,
                luck_mult=luck_mult,
                ooms=ooms,
                quarks=quarks,
            )
        elif loadout == "octeracts":
            if use_preboughts:
                pre_boughts = self.calculate_preboughts_for_cubes(ambrosia)
            best_loadout = self.best_cube_loadout_exact(
                ambrosia=ambrosia,
                pre_boughts=pre_boughts,
                luck_base=luck_base,
                luck_mult=luck_mult,
                quarks=quarks,
                p4x4=0,
            )
        return best_loadout

    def best_quark_loadout_exact(
        self, ambrosia, ooms, luck_base, luck_mult, pre_boughts=None
    ):

        names = [
            "ambrosiaTutorial",
            "ambrosiaQuarks1",
            "ambrosiaCubes1",
            "ambrosiaCubeQuark1",
            "ambrosiaLuck1",
            "ambrosiaLuckQuark1",
            "ambrosiaQuarks2",
        ]
        ranges = {}
        for name in names:
            start = 0
            stop = self._ambrosia_upgrades[name].max_level
            if pre_boughts is not None and name in pre_boughts:
                start = pre_boughts[name]
            ranges[name] = [i for i in range(start, stop + 1)]
            if name == "ambrosiaCubes1":
                if pre_boughts and name in pre_boughts:
                    ranges[name] = [pre_boughts[name]]
                else:
                    ranges[name] = [0, 20]
            if name == "ambrosiaLuck1":
                start_1 = 20
                if pre_boughts and name in pre_boughts:
                    start_1 = pre_boughts.get(name, 20)
                ranges[name] = [0] + [i for i in range(start_1, stop + 1)]
            if name == "ambrosiaTutorial":
                if pre_boughts and name in pre_boughts:
                    ranges[name] = [pre_boughts[name]]
                elif ambrosia > 100:
                    ranges[name] = [
                        self._ambrosia_upgrades["ambrosiaTutorial"].max_level
                    ]

        generator = self.recursive_yield(
            ambrosia=ambrosia,
            levels=names,
            pre_boughts=pre_boughts,
            ranges=ranges,
            luck_restrictor="ambrosiaCubeQuark1",
        )

        best_loadout = {name: 0 for name in names}
        best_quark_bonus = 0
        for affordable_levels in generator:
            quark_bonus = 1
            for name, max_level in affordable_levels.items():
                ambrosia_upgrade = self._ambrosia_upgrades[name]
                if name == "ambrosiaLuckQuark1":
                    luck = luck_base
                    luck += self._ambrosia_upgrades["ambrosiaLuck1"].luck(
                        affordable_levels["ambrosiaLuck1"]
                    )
                    quark_bonus *= ambrosia_upgrade.quarks(
                        max_level, luck * (1 + luck_mult)
                    )
                elif name == "ambrosiaCubeQuark1":
                    quark_bonus *= ambrosia_upgrade.quarks(max_level, ooms)
                elif name == "ambrosiaQuarks2":
                    quark_bonus *= ambrosia_upgrade.quarks(
                        max_level, affordable_levels["ambrosiaQuarks1"]
                    )
                else:
                    quark_bonus *= ambrosia_upgrade.quarks(max_level)
                if quark_bonus < best_quark_bonus:
                    continue
                best_quark_bonus = quark_bonus
                best_loadout = {k: v for (k, v) in affordable_levels.items()}
        return best_loadout

    def best_cube_loadout_exact(
        self, ambrosia, quarks, luck_base, luck_mult, p4x4=40, pre_boughts=None
    ):

        names = [
            "ambrosiaHyperflux",
            "ambrosiaTutorial",
            "ambrosiaCubes1",
            "ambrosiaQuarks1",
            "ambrosiaQuarkCube1",
            "ambrosiaLuck1",
            "ambrosiaLuckCube1",
            "ambrosiaCubes2",
        ]
        ranges = {}
        for name in names:
            start = 0
            stop = self._ambrosia_upgrades[name].max_level
            if pre_boughts is not None and name in pre_boughts:
                start = pre_boughts[name]
            ranges[name] = [i for i in range(start, stop + 1)]
            if name == "ambrosiaQuarks1":
                if pre_boughts and name in pre_boughts:
                    ranges[name] = [pre_boughts[name]]
                else:
                    ranges[name] = [0, 20]
            if name == "ambrosiaLuck1":
                start_1 = 20
                if pre_boughts and name in pre_boughts:
                    start_1 = pre_boughts.get(name, 20)
                # ranges[name] = [0] + [i for i in range(start_1, stop + 1)]
                ranges[name] = [0] + [start_1]
            if name == "ambrosiaTutorial":
                if pre_boughts and name in pre_boughts:
                    ranges[name] = [pre_boughts[name]]
                elif ambrosia > 100:
                    ranges[name] = [
                        self._ambrosia_upgrades["ambrosiaTutorial"].max_level
                    ]
        if p4x4 == 0:
            ranges["ambrosiaHyperflux"] = [0]

        generator = self.recursive_yield(
            ambrosia=ambrosia,
            levels=names,
            pre_boughts=pre_boughts,
            ranges=ranges,
            luck_restrictor="ambrosiaQuarkCube1",
        )

        best_loadout = {name: 0 for name in names}
        best_cubes_bonus = 0
        for loadout in generator:
            bonus = self.calculate_bonus(
                loadout=loadout,
                quarks=quarks,
                luck_base=luck_base,
                luck_mult=luck_mult,
                p4x4=p4x4,
            )
            if bonus["cubes"] <= best_cubes_bonus:
                continue
            best_cubes_bonus = bonus["cubes"]
            best_loadout = dict(loadout)
        return best_loadout

    def best_luck_loadout_exact(
        self, ambrosia, ooms, quarks, luck_base, luck_mult, pre_boughts=None
    ):

        names = [
            "ambrosiaTutorial",
            "ambrosiaQuarks1",
            "ambrosiaCubes1",
            "ambrosiaLuck1",
            "ambrosiaQuarkLuck1",
            "ambrosiaCubeLuck1",
            "ambrosiaLuck2",
        ]
        ranges = {}
        for name in names:
            start = 0
            stop = self._ambrosia_upgrades[name].max_level
            if pre_boughts is not None and name in pre_boughts:
                start = pre_boughts[name]
            ranges[name] = [i for i in range(start, stop + 1)]
            if name == "ambrosiaCubes1":
                if pre_boughts and name in pre_boughts:
                    ranges[name] = [pre_boughts[name]]
                else:
                    ranges[name] = [0, 20]
            if name == "ambrosiaQuarks1":
                if pre_boughts and name in pre_boughts:
                    ranges[name] = [pre_boughts[name]]
                else:
                    ranges[name] = [0, 20]
            if name == "ambrosiaTutorial":
                if pre_boughts and name in pre_boughts:
                    ranges[name] = [pre_boughts[name]]
                elif ambrosia > 100:
                    ranges[name] = [
                        self._ambrosia_upgrades["ambrosiaTutorial"].max_level
                    ]

        generator = self.recursive_yield(
            ambrosia=ambrosia,
            levels=names,
            pre_boughts=pre_boughts,
            ranges=ranges,
        )

        best_loadout = {name: 0 for name in names}
        best_luck_bonus = 0
        for loadout in generator:
            bonus = self.calculate_bonus(
                loadout=loadout,
                quarks=quarks,
                ooms=ooms,
                luck_base=luck_base,
                luck_mult=luck_mult,
            )
            if bonus["luck"] <= best_luck_bonus:
                continue
            best_luck_bonus = bonus["luck"]
            best_loadout = dict(loadout)
        return best_loadout


    def best_luck_loadout_greedy(
        self, ambrosia, ooms, quarks, luck_base, luck_mult, pre_boughts=None
    ):

        if ambrosia <= 0:
            return {}
        best_loadout = {"ambrosiaPatreon": 1}
        choices = []

        tutorial = self._ambrosia_upgrades["ambrosiaTutorial"]

        cubes1 = self._ambrosia_upgrades["ambrosiaCubes1"]
        luck1 = self._ambrosia_upgrades["ambrosiaLuck1"]
        quarks1 = self._ambrosia_upgrades["ambrosiaQuarks1"]

        quarkluck1 = self._ambrosia_upgrades["ambrosiaQuarkLuck1"]
        cubeluck1 = self._ambrosia_upgrades["ambrosiaCubeLuck1"]

        luck2 = self._ambrosia_upgrades["ambrosiaCubes2"]

        round=0
        while True:
            round+=1
            if choices:
                next_loadout = {}
                best_choice = {}
                best_price_to_luck_ratio = 0
                curr_luck_2 = best_loadout.get("ambrosiaLuck2", 0)
                has40 = any(x.get("ambrosiaLuck2",0) + curr_luck_2>=10 for x in choices)
                has40 = False
                curr_price = self.calculate_price(best_loadout)
                curr_bonus = self.calculate_bonus(
                    best_loadout,
                    ooms=ooms,
                    quarks=quarks,
                    luck_base=luck_base,
                    luck_mult=luck_mult,
                )
                if has40:
                    print("CURRENT LOADOUT: ", best_loadout)
                for choice in choices:
                    if not choice:
                        continue
                    loadout = dict(best_loadout)
                    for name, level in choice.items():
                        upgrade = self._ambrosia_upgrades[name]
                        new_level = loadout.get(name, 0) + level
                        loadout[name] = min(upgrade.max_level, new_level)
                    price = self.calculate_price(loadout)
                    bonus = self.calculate_bonus(
                        loadout,
                        ooms=ooms,
                        quarks=quarks,
                        luck_base=luck_base,
                        luck_mult=luck_mult,
                    )
                    price_to_luck_ratio = (bonus["luck"]-curr_bonus["luck"]) / (price - curr_price)
                    if price > ambrosia:
                        if has40:
                            print("DISQUALIFIED:", round, price_to_luck_ratio, choice)
                        continue
                    elif has40:
                        print("QUALIFIED:   ", round, price_to_luck_ratio, choice)
                    if price_to_luck_ratio < best_price_to_luck_ratio:
                        continue
                    best_choice = choice
                    best_price_to_luck_ratio = price_to_luck_ratio
                    next_loadout = dict(loadout)

                if next_loadout:
                    best_loadout = next_loadout
                    if has40:
                        print("WINNER       ", round, best_price_to_luck_ratio, best_choice)
                        print("="*79)
                else:
                    if has40:
                        print("NO WINNER")
                        print("="*79)
                    break

            choices = []
            tutorial_level = best_loadout.get("ambrosiaTutorial", 0)
            if tutorial_level < tutorial.max_level:
                choices.append({"ambrosiaTutorial": 1})
                continue

            luck1_level = best_loadout.get("ambrosiaLuck1", 0)
            if luck1_level < luck1.max_level:
                choices.append({"ambrosiaLuck1": 1})
                add_10 = math.ceil((luck1_level + 1) / 10) * 10 - luck1_level
                if add_10 > 1:
                    choices.append({"ambrosiaLuck1": add_10})

            quarks1_level = best_loadout.get("ambrosiaQuarks1", 0)
            if best_loadout.get("ambrosiaQuarkLuck1", 0) < quarkluck1.max_level:
                to_add = {
                    "ambrosiaLuck1": max(0, 30 - luck1_level),
                    "ambrosiaQuarks1": max(0, 20 - quarks1_level),
                    "ambrosiaQuarkLuck1": 1,
                }
                choices.append(to_add)

            cubes1_level = best_loadout.get("ambrosiaCubes1", 0)
            if best_loadout.get("ambrosiaCubeLuck1", 0) < cubeluck1.max_level:
                to_add = {
                    "ambrosiaLuck1": max(0, 30 - luck1_level),
                    "ambrosiaCubes1": max(0, 20 - cubes1_level),
                    "ambrosiaCubeLuck1": 1,
                }
                choices.append(to_add)

            luck2_level = best_loadout.get("ambrosiaLuck1", 0)
            if luck2_level < luck2.max_level:
                choices.append({"ambrosiaLuck2": 1, "ambrosiaLuck1": max(0, 40 - luck1_level)})
                add_10 = math.ceil((luck2_level + 1) / 10) * 10 - luck2_level
                if add_10 > 1:
                    choices.append({"ambrosiaLuck2": add_10, "ambrosiaLuck1": max(0, 40 - luck1_level)})

            if not choices:
                break
        return best_loadout

    def calculate_bonus(
        self, loadout, quarks=None, ooms=None, luck_base=None, luck_mult=None, p4x4=None
    ):
        ooms = 0 if ooms is None else ooms
        quarks = 0 if quarks is None else quarks
        luck_base = 0 if luck_base is None else luck_base
        luck_mult = 0 if luck_mult is None else luck_mult
        p4x4 = 0 if p4x4 is None else p4x4

        bonuses = {"quarks": 1, "cubes": 1, "octeracts": 1, "luck": 0}

        luck_1_bonus = self._ambrosia_upgrades["ambrosiaLuck1"].luck(
            loadout.get("ambrosiaLuck1", 0)
        )
        bonuses["luck"] += luck_1_bonus
        bonuses["luck"] += self._ambrosia_upgrades["ambrosiaCubeLuck1"].luck(
            loadout.get("ambrosiaCubeLuck1", 0), ooms
        )
        quark_luck = self._ambrosia_upgrades["ambrosiaQuarkLuck1"].luck(
            loadout.get("ambrosiaQuarkLuck1", 0), quarks
        )
        bonuses["luck"] += quark_luck
        bonuses["luck"] += self._ambrosia_upgrades["ambrosiaLuck2"].luck(
            loadout.get("ambrosiaLuck2", 0), loadout.get("ambrosiaLuck1", 0)
        )
        luck = (bonuses["luck"] + luck_base) * (1 + luck_mult)
        bonuses["luck"] *= 1 + luck_mult

        bonuses["quarks"] *= self._ambrosia_upgrades["ambrosiaQuarks1"].quarks(
            loadout.get("ambrosiaQuarks1", 0)
        )
        bonuses["quarks"] *= self._ambrosia_upgrades["ambrosiaLuckQuark1"].quarks(
            loadout.get("ambrosiaLuckQuark1", 0), luck
        )
        bonuses["quarks"] *= self._ambrosia_upgrades["ambrosiaCubeQuark1"].quarks(
            loadout.get("ambrosiaCubeQuark1", 0), ooms
        )
        bonuses["quarks"] *= self._ambrosia_upgrades["ambrosiaQuarks2"].quarks(
            loadout.get("ambrosiaQuarks2", 0), loadout.get("ambrosiaQuarks1", 0)
        )

        cube_1_bonus = self._ambrosia_upgrades["ambrosiaCubes1"].cubes(
            loadout.get("ambrosiaCubes1", 0)
        )
        bonuses["cubes"] *= cube_1_bonus

        luck_cube = self._ambrosia_upgrades["ambrosiaLuckCube1"].cubes(
            loadout.get("ambrosiaLuckCube1", 0), luck
        )
        bonuses["cubes"] *= luck_cube
        quark_cube_bonus = self._ambrosia_upgrades["ambrosiaQuarkCube1"].cubes(
            loadout.get("ambrosiaQuarkCube1", 0), quarks
        )
        bonuses["cubes"] *= quark_cube_bonus
        cube_2_bonus = self._ambrosia_upgrades["ambrosiaCubes2"].cubes(
            loadout.get("ambrosiaCubes2", 0), loadout.get("ambrosiaCubes1", 0)
        )
        bonuses["cubes"] *= cube_2_bonus
        bonuses["octeracts"] *= bonuses["cubes"]
        hyperflux_bonuses = self._ambrosia_upgrades["ambrosiaHyperflux"].cubes(
            loadout.get("ambrosiaHyperflux", 0), p4x4
        )
        bonuses["cubes"] *= hyperflux_bonuses

        return bonuses

    def calculate_price(self, loadout: dict[str, float]):
        total = 0
        for name, level in loadout.items():
            costs = self.cumulative_cost.get(name)
            if costs is None:
                continue
            total += costs.get(level, 0)
        return total


@dataclass
class SingularityUpgrade:
    name: str
    cost_per_level: float
    effect_formula: Callable[[float], float]
    cost_multiplier_formula: str = "Default"
    max_level: float = -1
    free_level: float = 0
    level: float = float("0")

    def effect(self, level=None):
        if level is None:
            level = self.level
        total_level = self.effective_level(level)
        return self.effect_formula(total_level)

    @property
    def effective_free_level(self):
        if self.free_level <= self.level:
            return self.free_level
        excess_levels = self.free_level - self.level
        return self.max_level + math.sqrt(excess_levels)

    def effective_level(self, softy: Optional[bool] = True):
        actual_free_levels = self.effective_free_level
        linear_levels = self.level + actual_free_levels
        polynomial_levels = 0

        if softy:
            exponent = 0.75
            polynomial_levels = math.pow(self.level * actual_free_levels, exponent)

        return max(linear_levels, polynomial_levels)

    def effect_for_next_level(self):
        return self.effect(self.level + 1) - self.effect(self.level)

    def get_cost_tnl(self, level=None):
        if level is None:
            level = self.level

        cost_multiplier = 1

        if level >= self.max_level and self.max_level > 0:
            cost_multiplier *= math.pow(4, level - self.max_level + 1)

        if self.cost_multiplier_formula == "Exponential2":
            return self.cost_per_level * math.sqrt(cost_multiplier) * math.pow(2, level)

        if self.cost_multiplier_formula == "Cubic":
            return (
                self.cost_per_level
                * cost_multiplier
                * (math.pow(level + 1, 3) - math.pow(level, 3))
            )

        if self.cost_multiplier_formula == "Quadratic":
            return (
                self.cost_per_level
                * cost_multiplier
                * (math.pow(level + 1, 2) - math.pow(level, 2))
            )

        if self.max_level == -1:
            if level >= 100:
                cost_multiplier *= level / 50
            if level >= 400:
                cost_multiplier *= level / 100

        if level >= self.max_level and self.max_level > 0:
            return 0

        return math.ceil(self.cost_per_level * (1 + level) * cost_multiplier)


def naive_optimizer_singularity(
    gq=float("1e22"),
    free_cube_flame_levels=0,
    free_citadel_levels=100,
    free_absinthe_levels=0,
):
    best_product = 0
    best_ratio = (1, 1, 1)
    seen_triples = {}

    upgrades = {
        "Citadel of Singularity": SingularityUpgrade(
            "Citadel of Singularity",
            500000,
            free_level=free_citadel_levels,
            level=0,
            effect_formula=lambda n: (1 + 0.02 * n) * (1 + (n // 10) / 100),
        ),
        "Cube Flame": SingularityUpgrade(
            "Cube Flame",
            1,
            free_level=free_cube_flame_levels,
            level=0,
            effect_formula=lambda n: 1 + 0.01 * n,
        ),
        "Octeract Absinthe": SingularityUpgrade(
            "Octeract Absinthe",
            20000,
            free_level=free_absinthe_levels,
            level=0,
            effect_formula=lambda n: 1 + 0.0125 * n,
        ),
    }

    info = {}

    for name, upgrade in upgrades.items():
        info[name] = []
        gq_spent = 0
        info[name].append({"gq_spent": 0, "level": 0, "cubes": 1, "octeracts": 1})
        while True:
            cost_for_next_upgrade = upgrade.get_cost_tnl(upgrade.level)
            if gq_spent + cost_for_next_upgrade > gq:
                break
            gq_spent += cost_for_next_upgrade
            upgrade.level += 1
            cubes_effect = upgrade.effect() if name != "Octeract Absinthe" else 1
            octeracts_effect = (
                upgrade.effect() if name != "Citadel of Singularity" else 1
            )
            info[name].append(
                {
                    "gq_spent": gq_spent,
                    "level": upgrade.level,
                    "cubes": cubes_effect,
                    "octeracts": octeracts_effect,
                }
            )

    def bisect_lookup(upgrade_name, gq_spending):
        idx = (
            bisect_right(
                [entry["gq_spent"] for entry in info[upgrade_name]], gq_spending
            )
            - 1
        )
        return info[upgrade_name][idx]

    i = 1
    seen_triples = {}
    previous_j = None
    for j in range(1, 100):
        best_k = 0
        for k in range(1, 100):
            total = i + j + k
            triplet = tuple([reduce_fraction(v, total) for v in [i, j, k]])
            if triplet in seen_triples:
                continue
            seen_triples[triplet] = True

            allocated_gq = [gq * ratio / total for ratio in [i, j, k]]
            result_flame = bisect_lookup("Cube Flame", allocated_gq[0])
            result_citadel = bisect_lookup("Citadel of Singularity", allocated_gq[1])
            result_absinthe = bisect_lookup("Octeract Absinthe", allocated_gq[2])

            multiplier_cubes = result_flame["cubes"] * result_citadel["cubes"]
            multiplier_octeracts = (
                result_flame["octeracts"] * result_absinthe["octeracts"]
            )
            product = multiplier_cubes * multiplier_octeracts
            if best_k is not None and product < best_k:
                break
            best_k = product

            if product > best_product:
                best_ratio = (i, j, k)
                best_product = product
                print(f"{100 * (multiplier_cubes-1):2.2e}%")
                print(f"{100 * (multiplier_octeracts-1):2.2e}%")
                print(f"{100 * (product):2.2e}%")
                print(best_ratio)
        if previous_j is not None and best_k < previous_j:
            break
        previous_j = best_k

    j = 1
    seen_triples = {}
    previous_i = None
    for i in range(1, 100):
        best_k = 0
        for k in range(1, 100):
            total = i + j + k
            triplet = tuple([reduce_fraction(v, total) for v in [i, j, k]])
            if triplet in seen_triples:
                continue
            seen_triples[triplet] = True

            allocated_gq = [gq * ratio / total for ratio in [i, j, k]]
            result_flame = bisect_lookup("Cube Flame", allocated_gq[0])
            result_citadel = bisect_lookup("Citadel of Singularity", allocated_gq[1])
            result_absinthe = bisect_lookup("Octeract Absinthe", allocated_gq[2])

            multiplier_cubes = result_flame["cubes"] * result_citadel["cubes"]
            multiplier_octeracts = (
                result_flame["octeracts"] * result_absinthe["octeracts"]
            )
            product = multiplier_cubes * multiplier_octeracts
            if best_k is not None and product < best_k:
                break
            best_k = product

            if product > best_product:
                best_ratio = (i, j, k)
                best_product = product
                print(f"{100 * (multiplier_cubes-1):2.2e}%")
                print(f"{100 * (multiplier_octeracts-1):2.2e}%")
                print(f"{100 * (product):2.2e}%")
                print(best_ratio)
        if previous_i is not None and best_k < previous_i:
            break

    k = 1
    seen_triples = {}
    previous_i = None
    for i in range(1, 100):
        best_j = 0
        for j in range(1, 100):
            total = i + j + k
            triplet = tuple([reduce_fraction(v, total) for v in [i, j, k]])
            if triplet in seen_triples:
                continue
            seen_triples[triplet] = True

            allocated_gq = [gq * ratio / total for ratio in [i, j, k]]
            result_flame = bisect_lookup("Cube Flame", allocated_gq[0])
            result_citadel = bisect_lookup("Citadel of Singularity", allocated_gq[1])
            result_absinthe = bisect_lookup("Octeract Absinthe", allocated_gq[2])

            multiplier_cubes = result_flame["cubes"] * result_citadel["cubes"]
            multiplier_octeracts = (
                result_flame["octeracts"] * result_absinthe["octeracts"]
            )
            product = multiplier_cubes * multiplier_octeracts
            if best_j is not None and product < best_j:
                break
            best_k = product

            if product > best_product:
                best_ratio = (i, j, k)
                best_product = product
                print(f"{100 * (multiplier_cubes-1):2.2e}%")
                print(f"{100 * (multiplier_octeracts-1):2.2e}%")
                print(f"{100 * (product):2.2e}%")
                print(best_ratio)
        if previous_i is not None and best_j < previous_i:
            break

    return best_ratio, best_product


def singularity_purchases(
    gq: float,
    flame_ratio: float = 1,
    citadel_ratio: float = 1,
    octeract_ratio: float = 1,
    current_flame_level: int = 1,
    current_citadel_level: int = 1,
    current_absinthe_level: int = 1,
    free_flame_levels: int = 0,
    free_citadel_levels: int = 100,
    free_absinthe_levels: int = 0,
):
    """
    Optimize the spread of upgrades for 'Citadel of Singularity', 'Cube Flame', and 'Octeract Absinthe'.

    Parameters:
        current_flame_level (int): Current level of the Cube Flame upgrade.
        current_citadel_level (int): Current level of the Citadel of Singularity upgrade.
        current_absinthe_level (int): Current level of the Octeract Absinthe upgrade.
        gq (float): Amount of resources available for upgrading.
        free_flame_levels (int): Free initial levels for Cube Flame upgrade. Default is 0.
        free_citadel_levels (int): Free initial levels for Citadel of Singularity upgrade. Default is 100.
        free_absinthe_levels (int): Free initial levels for Octeract Absinthe upgrade. Default is 0.
        target_ratio (float): The desired ratio of effects. Default is 1.0.

    Returns:
        Tuple[Dict[str, int], float]: A tuple containing the dictionary of upgrade spread and the remaining resources.
    """
    upgrades = {
        "Citadel of Singularity": SingularityUpgrade(
            "Citadel of Singularity",
            500000,
            free_level=free_citadel_levels,
            level=current_citadel_level,
            effect_formula=lambda n: (1 + 0.02 * n) * (1 + (n // 10) / 100),
        ),
        "Cube Flame": SingularityUpgrade(
            "Cube Flame",
            1,
            free_level=free_flame_levels,
            level=current_flame_level,
            effect_formula=lambda n: 1 + 0.01 * n,
        ),
        "Octeract Absinthe": SingularityUpgrade(
            "Octeract Absinthe",
            20000,
            free_level=free_absinthe_levels,
            level=current_absinthe_level,
            effect_formula=lambda n: 1 + 0.0125 * n,
        ),
    }

    total_ratio = flame_ratio + citadel_ratio + octeract_ratio
    ratios = {
        "Cube Flame": flame_ratio / total_ratio,
        "Citadel of Singularity": citadel_ratio / total_ratio,
        "Octeract Absinthe": octeract_ratio / total_ratio,
    }
    results = {}

    for name, ratio in ratios.items():
        results[name] = {}
        gq_to_spend = gq * ratio
        gq_spent = 0
        while (
            gq_spent + upgrades[name].get_cost_tnl(upgrades[name].level) < gq_to_spend
        ):
            gq_spent += upgrades[name].get_cost_tnl(upgrades[name].level)
            upgrades[name].level += 1
        results[name]["spent"] = gq_spent
        results[name]["level"] = upgrades[name].level
        if name == "Cube Flame":
            results[name]["cubes"] = upgrades[name].effect()
            results[name]["octeracts"] = upgrades[name].effect()
        elif name == "Citadel of Singularity":
            results[name]["cubes"] = upgrades[name].effect()
            results[name]["octeracts"] = 1
        elif name == "Octeract Absinthe":
            results[name]["cubes"] = 1
            results[name]["octeracts"] = upgrades[name].effect()

    return results


def optimize_upgrade_spread_by_product(
    gq: float,
    current_flame_level: int = 1,
    current_citadel_level: int = 1,
    current_absinthe_level: int = 1,
    free_flame_levels: int = 0,
    free_citadel_levels: int = 100,
    free_absinthe_levels: int = 0,
    target_ratio: float = 1.0,
) -> tuple[dict[str, int], float]:
    """
    Optimize the spread of upgrades for 'Citadel of Singularity', 'Cube Flame', and 'Octeract Absinthe'.

    Parameters:
        current_flame_level (int): Current level of the Cube Flame upgrade.
        current_citadel_level (int): Current level of the Citadel of Singularity upgrade.
        current_absinthe_level (int): Current level of the Octeract Absinthe upgrade.
        gq (float): Amount of resources available for upgrading.
        free_flame_levels (int): Free initial levels for Cube Flame upgrade. Default is 0.
        free_citadel_levels (int): Free initial levels for Citadel of Singularity upgrade. Default is 100.
        free_absinthe_levels (int): Free initial levels for Octeract Absinthe upgrade. Default is 0.
        target_ratio (float): The desired ratio of effects. Default is 1.0.

    Returns:
        Tuple[Dict[str, int], float]: A tuple containing the dictionary of upgrade spread and the remaining resources.
    """
    upgrades = {
        "Citadel of Singularity": SingularityUpgrade(
            "Citadel of Singularity",
            500000,
            free_level=free_citadel_levels,
            level=current_citadel_level,
            effect_formula=lambda n: (1 + 0.02 * n) * (1 + (n // 10) / 100),
        ),
        "Cube Flame": SingularityUpgrade(
            "Cube Flame",
            1,
            free_level=free_flame_levels,
            level=current_flame_level,
            effect_formula=lambda n: 1 + 0.01 * n,
        ),
        "Octeract Absinthe": SingularityUpgrade(
            "Octeract Absinthe",
            20000,
            free_level=free_absinthe_levels,
            level=current_absinthe_level,
            effect_formula=lambda n: 1 + 0.0125 * n,
        ),
    }

    upgrade_spread = {key: 0 for key in upgrades.keys()}
    upgrade_cost = {key: 0.0 for key in upgrades.keys()}
    remaining_gq = gq

    while remaining_gq > 0:

        best_upgrade_name = "Citadel of Singularity"
        best_upgrade = upgrades[best_upgrade_name]
        best_upgrade_cost = best_upgrade.get_cost_tnl()
        best_cost_effect_ratio = -float("Inf")

        flame_effect = upgrades["Cube Flame"].effect()
        base_effect_cubes = upgrades["Citadel of Singularity"].effect() * flame_effect
        base_effect_octeracts = flame_effect * upgrades["Octeract Absinthe"].effect()
        for name, upgrade in upgrades.items():
            cost_to_next_level = upgrade.get_cost_tnl()
            effect_octeracts = base_effect_octeracts
            effect_cube = base_effect_cubes
            if name == "Citadel of Singularity":
                effect_cube = upgrade.effect(upgrade.level + 1) * flame_effect
            elif name == "Cube Flame":
                effect_cube = (
                    upgrade.effect(upgrade.level + 1)
                    * upgrades["Citadel of Singularity"].effect()
                )
                effect_octeracts = (
                    upgrade.effect(upgrade.level + 1)
                    * upgrades["Octeract Absinthe"].effect()
                )
            elif name == "Octeract Absinthe":
                effect_octeracts = upgrade.effect(upgrade.level + 1) * flame_effect
            cost_effect_ratio = effect_cube * effect_octeracts / cost_to_next_level

            if remaining_gq > float("1e21") and remaining_gq < float("1.2e21"):
                # print(f"{name}=cost: {cost_to_next_level:2.2e} effect_increase: {effect_increase} ratio: {cost_effect_ratio}")
                pass

            if cost_effect_ratio > best_cost_effect_ratio:
                best_upgrade_name = name
                best_upgrade = upgrade
                best_cost_effect_ratio = cost_effect_ratio
                best_upgrade_cost = cost_to_next_level

        if remaining_gq > float("1e21") and remaining_gq < float("1.2e21"):
            print()
        if remaining_gq < best_upgrade_cost or best_cost_effect_ratio < 0:
            break

        remaining_gq -= best_upgrade_cost
        upgrade_cost[best_upgrade_name] += best_upgrade_cost
        upgrade_spread[best_upgrade_name] += 1
        upgrades[best_upgrade_name].level += 1

    pprint(", ".join(f"{k}={v:2.2e}" for k, v in upgrade_cost.items()))
    multiplier_cubes = 1
    for name, up in upgrades.items():
        if name != "Octeract Absinthe":
            multiplier_cubes *= up.effect()
    multiplier_octeracts = 1
    for name, up in upgrades.items():
        if name != "Citadel of Singularity":
            multiplier_octeracts *= up.effect()
    print(f"{multiplier_cubes=:2.2e}")
    print(f"{multiplier_octeracts=:2.2e}")
    print(remaining_gq, sum(upgrade_cost.values()))

    return upgrade_spread, remaining_gq


def optimize_upgrade_spread_by_effect(
    current_flame_level: int,
    current_citadel_level: int,
    current_absinthe_level: int,
    gq: float,
    free_flame_levels: int = 0,
    free_citadel_levels: int = 100,
    free_absinthe_levels: int = 0,
    target_ratio: float = 1.0,
) -> tuple[dict[str, int], float]:
    """
    Optimize the spread of upgrades for 'Citadel of Singularity', 'Cube Flame', and 'Octeract Absinthe'.

    Parameters:
        current_flame_level (int): Current level of the Cube Flame upgrade.
        current_citadel_level (int): Current level of the Citadel of Singularity upgrade.
        current_absinthe_level (int): Current level of the Octeract Absinthe upgrade.
        gq (float): Amount of resources available for upgrading.
        free_flame_levels (int): Free initial levels for Cube Flame upgrade. Default is 0.
        free_citadel_levels (int): Free initial levels for Citadel of Singularity upgrade. Default is 100.
        free_absinthe_levels (int): Free initial levels for Octeract Absinthe upgrade. Default is 0.
        target_ratio (float): The desired ratio of effects. Default is 1.0.

    Returns:
        Tuple[Dict[str, int], float]: A tuple containing the dictionary of upgrade spread and the remaining resources.
    """
    upgrades = {
        "Citadel of Singularity": SingularityUpgrade(
            "Citadel of Singularity",
            500000,
            free_level=free_citadel_levels,
            level=current_citadel_level,
            effect_formula=lambda n: (1 + 0.02 * n) * (1 + (n // 10) / 100),
        ),
        "Cube Flame": SingularityUpgrade(
            "Cube Flame",
            1,
            free_level=free_flame_levels,
            level=current_flame_level,
            effect_formula=lambda n: 1 + 0.01 * n,
        ),
        "Octeract Absinthe": SingularityUpgrade(
            "Octeract Absinthe",
            20000,
            free_level=free_absinthe_levels,
            level=current_absinthe_level,
            effect_formula=lambda n: 1 + 0.0125 * n,
        ),
    }

    upgrade_spread = {key: 0 for key in upgrades.keys()}
    upgrade_cost = {key: 0.0 for key in upgrades.keys()}
    remaining_gq = gq
    print(f"{upgrades['Cube Flame'].get_cost_tnl() :2.2e}")

    while remaining_gq > 0:
        current_effects = {name: upgrade.effect() for name, upgrade in upgrades.items()}
        current_cube_effect = (
            current_effects["Cube Flame"] * current_effects["Citadel of Singularity"]
        )
        current_octeract_effect = (
            current_effects["Octeract Absinthe"]
            * current_effects["Citadel of Singularity"]
        )

        best_upgrade_name = "Citadel of Singularity"
        best_upgrade = upgrades[best_upgrade_name]
        best_upgrade_cost = best_upgrade.get_cost_tnl()
        best_cost_effect_ratio = -float("Inf")

        for name, upgrade in upgrades.items():
            cost_to_next_level = upgrade.get_cost_tnl()

            new_cube_effect = current_cube_effect
            if name == "Citadel of Singularity":
                new_cube_effect = (
                    upgrade.effect(upgrade.level + 1) * current_effects["Cube Flame"]
                )

            new_octeract_effect = current_octeract_effect
            if name == "Octeract Absinthe":
                new_octeract_effect = (
                    upgrade.effect(upgrade.level + 1) * current_effects["Cube Flame"]
                )

            if name == "Cube Flame":
                new_cube_effect = (
                    upgrade.effect(upgrade.level + 1)
                    * current_effects["Citadel of Singularity"]
                )
                new_octeract_effect = (
                    upgrade.effect(upgrade.level + 1)
                    * current_effects["Octeract Absinthe"]
                )

            combined_effect = target_ratio * new_cube_effect + new_octeract_effect
            cost_effect_ratio = combined_effect / cost_to_next_level

            if cost_effect_ratio > best_cost_effect_ratio:
                best_upgrade_name = name
                best_upgrade = upgrade
                best_cost_effect_ratio = cost_effect_ratio
                best_upgrade_cost = cost_to_next_level

        if remaining_gq < best_upgrade_cost:
            break

        remaining_gq -= best_upgrade_cost
        upgrade_cost[best_upgrade_name] += best_upgrade_cost
        upgrade_spread[best_upgrade_name] += 1
        upgrades[best_upgrade_name].level += 1

    pprint(upgrades)
    pprint(upgrade_cost)
    print(remaining_gq, sum(upgrade_cost.values()))

    return upgrade_spread, remaining_gq


geometry = Geometry(config_file=str(Path(__file__).parent / "geometry.json"))
# challenges
space_between_sing_shop_items = 9

# Create an Actions instance with the pre-configured Geometry instance
actions = Actions(geometry=geometry)
actions.x_scale = 1 / 1.75
actions.y_scale = 1 / 1.75

pre_c10_tabs = [
    "buildings",
    "upgrades",
    "achievements",
    "runes",
    "challenges",
    "research",
    "anthill",
    "singularity",
    "settings",
    "shop",
]
pre_c11_tabs = [
    "buildings",
    "upgrades",
    "achievements",
    "runes",
    "challenges",
    "research",
    "anthill",
    "cubes",
    "singularity",
    "settings",
    "shop",
]
post_c15_tabs = [
    "buildings",
    "upgrades",
    "achievements",
    "runes",
    "challenges",
    "research",
    "anthill",
    "cubes",
    "corruption",
    "singularity",
    "settings",
    "shop",
]


def get_tabs():
    if STATE["HIGHEST_BEATEN_CHALLENGE"] < 10:
        return pre_c10_tabs
    elif STATE["HIGHEST_BEATEN_CHALLENGE"] < 11:
        return pre_c11_tabs
    return post_c15_tabs


def go_to_tab(next, current=None):
    curr = STATE.get("CURRENT_TAB", "")
    if curr == "":
        go_to_buildings_tab()
        curr = STATE["CURRENT_TAB"]
    if current is not None:
        curr = current
    if curr == next:
        return (curr, next)

    dirs = {}
    tabs = get_tabs()

    current_index = tabs.index(curr)
    next_index = tabs.index(next)
    directions = {
        "right": (next_index - current_index) % len(tabs),
        "left": (current_index - next_index) % len(tabs),
    }

    if curr in [
        "buildings",
        "upgrades",
        "achievements",
        "runes",
        "challenges",
    ] and next in [
        "singularity",
        "settings",
        "shop",
    ]:
        for _ in range(directions["left"]):
            actions.perform_sequence(f"hotkey:tab:previous")
    elif next in [
        "buildings",
        "upgrades",
        "achievements",
        "runes",
        "challenges",
    ] and curr in [
        "singularity",
        "settings",
        "shop",
    ]:
        for _ in range(directions["right"]):
            actions.perform_sequence(f"hotkey:tab:next")
    elif STATE["HIGHEST_BEATEN_CHALLENGE"] >= 14:
        actions.perform_sequence(f"tab:{next}{c()}")
    else:
        if directions["right"] < directions["left"]:
            for _ in range(directions["right"]):
                actions.perform_sequence(f"hotkey:tab:next")
        else:
            for _ in range(directions["left"]):
                actions.perform_sequence(f"hotkey:tab:previous")
    STATE["CURRENT_TAB"] = next
    return (curr, next)

    # actions.perform_sequence(f"hotkey:tab:next")
    # STATE["CURRENT_TAB"] = next
    # return (curr, next)


space_between_tabs = 12.9
for tabs, c10_switch in [
    (pre_c10_tabs, ":C9"),
    (pre_c11_tabs, ":C10"),
    (post_c15_tabs, ""),
]:
    building = geometry.get_rectangle(f"tab:buildings{c10_switch}")
    if building is None:
        continue
    for i, tab in enumerate(tabs):
        name = f"tab:{tab}{c10_switch}"
        if i != 0:
            geometry.add_rectangle(
                name=name,
                x=building.x + i * (building.width + space_between_tabs),
                y=building.y,
                width=building.width,
                height=building.height,
            )
        actions.add_sequence(name, [{"type": "click", "name": name}])

go_to_challenge_tab = []
challenge_ten = geometry.get_rectangle(name="challenge:C10:highest_beaten:C9")
offset_per_completion = 5
space_between_challenges = 8.7
if challenge_ten is not None:
    offset_per_completion = 77
    for highest_beaten in range(8, 15):
        offset_h = max(highest_beaten, 9) - 9
        tabs_2_click = []
        #    {"type": "click", "name": f"tab:challenges{c(highest_beaten)}"},
        #    {"type": "click", "name": "subtab:challenges_normal"},
        # ]
        for current in range(1, highest_beaten + 2):
            offset_c = current - 10
            # print(f"{highest_beaten=}, {current=}, {offset_h}, {offset_c}")
            name = f"challenge:C{current}:highest_beaten:C{highest_beaten}"
            name_click = f"challenge:C{current}:highest_beaten:C{highest_beaten}:click"
            click_challenge = [{"type": "click", "name": name}]
            actions.add_sequence(name, tabs_2_click + click_challenge + click_challenge)
            actions.add_sequence(name_click, tabs_2_click + click_challenge)
            if highest_beaten == 9 and current == 10:
                continue
            geometry.add_rectangle(
                name=name,
                x=challenge_ten.x
                + offset_c * (challenge_ten.width + space_between_challenges)
                - offset_h * offset_per_completion,
                y=challenge_ten.y,
                width=challenge_ten.width,
                height=challenge_ten.height,
            )

s1x1 = geometry.get_rectangle(name="sing_shop:s1x1")
if s1x1 is not None:
    pairs = []
    for y in range(1, 6):
        for x in range(1, 15):
            if y == 1 and x == 1:
                continue
            elif (y == 5 and x == 1) or (y == 5 and x == 14):
                continue
            pairs.append([y, x])
    for y, x in pairs:
        geometry.add_rectangle(
            name=f"singularity_shop:s{y}x{x}",
            x=s1x1.x + (x - 1) * (s1x1.width + space_between_sing_shop_items),
            y=s1x1.y + (y - 1) * (s1x1.height + space_between_sing_shop_items),
            width=s1x1.width,
            height=s1x1.height,
        )
        actions.add_sequence(
            f"singularity_shop:buy:s{y}x{x}:custom",
            [
                {"type": "click", "name": "subtab:singularity_shop"},
                {
                    "type": "click",
                    "name": f"singularity_shop:s{y}x{x}",
                    "modifiers": [Key.shift],
                },
                {"type": "type_text", "input_placeholder": True},
                {"type": "key_press", "button": "enter"},
                {"type": "key_press", "button": "enter"},
            ],
        )
        actions.add_sequence(
            f"singularity_shop:buy:s{y}x{x}:x1",
            [
                {"type": "click", "name": "subtab:singularity_shop"},
                {"type": "click", "name": f"singularity_shop:s{y}x{x}"},
                {"type": "key_press", "button": "enter"},
                {"type": "key_press", "button": "enter"},
            ],
        )
s1x1 = geometry.get_rectangle(name="quark_shop:s1x1")
s1x1_level = geometry.get_rectangle(name="quark_shop:s1x1:level")
space_between_quark_shop_items_x = 12
space_between_quark_shop_items_y = 4
if s1x1 is not None and s1x1_level is not None:
    pairs = []
    for y in [1]:
        for x in range(1, 9):
            if y == 1 and x == 1:
                continue
            pairs.append([y, x])
    for y, x in pairs:
        geometry.add_rectangle(
            name=f"quark_shop:s{y}x{x}",
            x=s1x1.x + (x - 1) * (s1x1.width + space_between_quark_shop_items_x),
            y=s1x1.y + (y - 1) * (s1x1.height + space_between_quark_shop_items_y),
            width=s1x1.width,
            height=s1x1.height,
        )
        geometry.add_rectangle(
            name=f"quark_shop:s{y}x{x}:level",
            x=s1x1_level.x + (x - 1) * (s1x1.width + space_between_quark_shop_items_x),
            y=s1x1_level.y + (y - 1) * (s1x1.height + space_between_quark_shop_items_y),
            width=s1x1_level.width,
            height=s1x1_level.height,
        )
        actions.add_sequence(
            f"quark_shop:buy:s{y}x{x}:custom",
            [
                {
                    "type": "click",
                    "name": f"quark_shop:s{y}x{x}",
                    "modifiers": [Key.shift],
                },
                {"type": "type_text", "input_placeholder": True},
                {"type": "key_press", "button": "enter"},
                {"type": "key_press", "button": "enter"},
            ],
        )
        actions.add_sequence(
            f"quark_shop:buy:s{y}x{x}:x1",
            [
                {"type": "click", "name": f"quark_shop:s{y}x{x}"},
                {"type": "key_press", "button": "enter"},
                {"type": "key_press", "button": "enter"},
            ],
        )

# Time to build the cube subtab
cubes = ["tributes", "gifts", "benedictions", "platonics"]
wow_subtabs = cubes + ["upgrades:cubes", "upgrades:platonic", "forge"]
cube_amounts = ["x1", "10%", "50%", "custom", "all", "auto"]
tributes = geometry.get_rectangle("subtab:tributes")
tributes_x1 = geometry.get_rectangle("tributes:buy:x1")
space_between_amounts = 11
space_between_tabs = 11
if tributes is not None:
    for i, tab in enumerate(wow_subtabs):
        name = f"subtab:{tab}"
        if i == 1:
            continue
        geometry.add_rectangle(
            name=name,
            x=tributes.x,
            y=tributes.y + i * (space_between_tabs + tributes.height),
            width=tributes.width,
            height=tributes.height,
        )
        actions.add_sequence(
            seq_name=name,
            sequence=[
                {"type": "click", "name": name},
            ],
        )
if tributes_x1 is not None:
    for cube_name in cubes:
        for i, amount in enumerate(cube_amounts):
            name = f"{cube_name}:buy:{amount}"
            if not (cube_name == "tributes" and i == 0):
                geometry.add_rectangle(
                    name=name,
                    x=tributes_x1.x + i * (space_between_amounts + tributes_x1.width),
                    y=tributes_x1.y,
                    width=tributes_x1.width,
                    height=tributes_x1.height,
                )
            dos: list[dict[str, str | bool]] = [
                {"type": "click", "name": f"subtab:{cube_name}"},
                {"type": "click", "name": f"{cube_name}:buy:{amount}"},
            ]
            if amount == "custom":
                dos.extend(
                    [
                        {"type": "type_text", "input_placeholder": True},
                        {"type": "key_press", "button": "enter"},
                        {"type": "key_press", "button": "enter"},
                    ]
                )
            actions.add_sequence(seq_name=name, sequence=dos)

# building = geometry.get_rectangle("upgrades")
# building = geometry.get_rectangle("challenges:C10_text:highest_beaten:C10")
ocr = autosynergism.ocr.OCR(geometry=geometry)

for rectangle in geometry.rectangles:
    actions.add_sequence(
        rectangle,
        [
            {"type": "click", "name": rectangle},
        ],
    )

# =======================================================
# SINGULARITY
# =======================================================

# Sing Shop
# -----------
sing_shop_names = {
    "offerings": (2, 12),
    "obtainium": (3, 1),
    "cube_flame": (3, 4),
    "fake_citadel": (3, 7),
    "octeract_absinthe": (3, 4),
    "octeract_absinthe": (3, 4),
}
for i in range(4):
    sing_shop_names[f"ambrosia_luck_{i+1}"] = (5, 6 + i)
    sing_shop_names[f"blueberry_speed_{i+1}"] = (5, 10 + i)
for name, (y, x) in sing_shop_names.items():
    actions.add_sequence(
        f"singularity_shop:buy:{name}:custom",
        [
            {"type": "click", "name": "subtab:singularity_shop"},
            {
                "type": "click",
                "name": f"singularity_shop:s{y}x{x}",
                "modifiers": [Key.shift],
            },
            {"type": "type_text", "input_placeholder": True},
            {"type": "key_press", "button": "enter"},
            {"type": "key_press", "button": "enter"},
        ],
    )
    actions.add_sequence(
        f"singularity_shop:buy:{name}:x1",
        [
            {"type": "click", "name": "subtab:singularity_shop"},
            {"type": "click", "name": f"singularity_shop:s{y}x{x}"},
            {"type": "key_press", "button": "enter"},
            {"type": "key_press", "button": "enter"},
        ],
    )

actions.add_sequence(
    "reset_current_sing",
    [
        {"type": "click", "name": "subtab:challenges_exalt"},
        {"type": "click", "name": "exalt:4"},
        {"type": "key_press", "button": "enter", "delay": 0.1},
        {"type": "key_press", "button": "enter", "delay": 0.1},
        {"type": "key_press", "button": "enter", "delay": 0.1},
        {"type": "key_press", "button": "enter", "delay": 0.1},
        {"type": "key_press", "button": "enter", "delay": 0.1},
        {"type": "key_press", "button": "enter", "delay": 0.1},
        {"type": "click", "name": "tab:challenges:C9"},
        {"type": "click", "name": "subtab:challenges_exalt"},
        {"type": "click", "name": "exalt:4"},
        {"type": "key_press", "button": "enter", "delay": 0.1},
        {"type": "key_press", "button": "enter", "delay": 0.1},
        {"type": "key_press", "button": "enter", "delay": 0.1},
        {"type": "key_press", "button": "enter", "delay": 0.1},
        {"type": "key_press", "button": "enter", "delay": 0.1},
        {"type": "key_press", "button": "enter", "delay": 0.1},
    ],
)


def reset_current_sing():
    go_to_tab("challenges")
    actions.perform_sequence("reset_current_sing")


# AMBROSIA
# -----------
for c_switch in ["", ":C9", ":C10"]:
    actions.add_sequence(
        f"subtab:ambrosia{c_switch}",
        [
            {"type": "click", "name": f"tab:singularity{c_switch}"},
            {"type": "click", "name": "subtab:ambrosia"},
        ],
    )
loadouts = ["max_quarks", "max_cubes", "max_luck", "max_octeracts"]
for i, loadout_name in enumerate(loadouts, start=1):
    actions.add_sequence(
        f"ambrosia:loadout:{loadout_name}",
        [
            {"type": "click", "name": f"ambrosia:loadout_{i}"},
            {"type": "key_press", "button": "enter"},
            {"type": "key_press", "button": "enter"},
        ],
    )
# ===========================================================================
#    WOW! Cubes
# ===========================================================================
actions.add_sequence(
    "qhept:buy:custom",
    [
        {"type": "click", "name": "tab:cubes"},
        {"type": "click", "name": "subtab:forge"},
        {"type": "click", "name": "qhept:craft"},
        {"type": "type_text", "input_placeholder": True},
        {"type": "key_press", "button": "enter", "delay": 0.1},
        {"type": "key_press", "button": "enter", "delay": 0.1},
    ],
)
actions.add_sequence(
    "qhept:buy:max",
    [
        {"type": "click", "name": "tab:cubes"},
        {"type": "click", "name": "subtab:forge"},
        {"type": "click", "name": "qhept:max"},
        {"type": "key_press", "button": "enter", "delay": 0.1},
        {"type": "key_press", "button": "enter", "delay": 0.1},
    ],
)
actions.add_sequence(
    "qhept:expand",
    [
        {"type": "click", "name": "tab:cubes"},
        {"type": "click", "name": "subtab:forge"},
        {"type": "click", "name": "qhept:expand"},
        {"type": "key_press", "button": "enter", "delay": 0.1},
        {"type": "key_press", "button": "enter", "delay": 0.1},
    ],
)
# ======
#  SETTINGS
# ======
subtabs = [
    "settings",
    "languages",
    "credits",
    "stats_for_nerds",
    "reset_history",
    "ascend_history",
    "hotkeys",
]
space_between_tabs_in_settings = 22
settings_rectangle = geometry.get_rectangle("subtab:settings")
if settings_rectangle is not None:
    for i, subtab in enumerate(subtabs):
        if i == 0:
            continue
        geometry.add_rectangle(
            name=f"subtab:{subtab}",
            x=settings_rectangle.x
            + i * (settings_rectangle.width + space_between_tabs_in_settings),
            y=settings_rectangle.y,
            width=settings_rectangle.width,
            height=settings_rectangle.height,
        )
actions.add_sequence(
    "settings:daily",
    [
        {"type": "click", "name": "subtab:settings"},
        {"type": "click", "name": "settings:daily"},
        {"type": "key_press", "button": "enter"},
        {"type": "key_press", "button": "enter"},
        {"type": "key_press", "button": "enter"},
    ],
)
actions.add_sequence(
    "settings:promotion_code",
    [
        {"type": "click", "name": "tab:settings"},
        {"type": "click", "name": "subtab:settings"},
        {"type": "click", "name": "settings:promotion_code"},
        {"type": "type_text", "input_placeholder": True},
        {"type": "key_press", "button": "enter", "delay": 0.1},
        {"type": "key_press", "button": "enter", "delay": 0.1},
    ],
)
# ===========================================================================
#    HOTKEYS
# ===========================================================================
actions.add_sequence(
    "hotkey:tab:previous",
    [
        {"type": "key_press", "button": "left"},
    ],
)
actions.add_sequence(
    "hotkey:tab:next",
    [
        {"type": "key_press", "button": "right"},
    ],
)
actions.add_sequence(
    "hotkey:autochallenge",
    [
        {"type": "key_press", "button": "c"},
    ],
)
actions.add_sequence(
    "click:antsac",
    [
        {"type": "click", "name": "tab:anthill"},
        {"type": "click", "name": "anthill:sac"},
        {"type": "click", "name": "anthill:sac"},
    ],
)
actions.add_sequence(
    "hotkey:antsac",
    [
        {"type": "key_press", "button": "s", "delay": 0.1},
    ],
)
actions.add_sequence(
    "hotkey:prestige",
    [
        {"type": "key_press", "button": "p"},
    ],
)
actions.add_sequence(
    "hotkey:transcend",
    [
        {"type": "key_press", "button": "t"},
    ],
)
actions.add_sequence(
    "hotkey:reincarnate",
    [
        {"type": "key_press", "button": "r"},
    ],
)
actions.add_sequence(
    "hotkey:ascend",
    [
        {"type": "key_press", "button": "a", "modifiers": [Key.shift]},
    ],
)
actions.add_sequence(
    "hotkey:enter",
    [
        {"type": "key_press", "button": "enter", "delay": 0.1},
    ],
)
actions.add_sequence(
    "hotkey:add:x1",
    [
        {"type": "key_press", "button": "d", "modifiers": [Key.shift], "delay": 0.1},
    ],
)
actions.add_sequence(
    "hotkey:exit_challenge",
    [
        {"type": "key_press", "button": "e"},
    ],
)
actions.add_sequence(
    "hotkey:exit_all_challenges",
    [
        {"type": "key_press", "button": "e", "modifiers": [Key.shift]},
    ],
)
# ===========================================================================
#    CORRUPTIONS
# ===========================================================================
actions.add_sequence(
    "corruption_c14",
    [
        {"type": "key_press", "button": "1", "modifiers": [Key.shift]},
    ],
)
actions.add_sequence(
    "corruption_c14",
    [
        {"type": "key_press", "button": "1", "modifiers": [Key.shift]},
    ],
)
actions.add_sequence(
    "corruption_preplat",
    [
        {"type": "key_press", "button": "2", "modifiers": [Key.shift]},
    ],
)
actions.add_sequence(
    "corruption_w5x10max",
    [
        {"type": "key_press", "button": "3", "modifiers": [Key.shift]},
    ],
)
actions.add_sequence(
    "corruption_p2x2max",
    [
        {"type": "key_press", "button": "4", "modifiers": [Key.shift]},
    ],
)
actions.add_sequence(
    "corruption_p3x1",
    [
        {"type": "key_press", "button": "5", "modifiers": [Key.shift]},
    ],
)
actions.add_sequence(
    "corruption_p4x2",
    [
        {"type": "key_press", "button": "6", "modifiers": [Key.shift]},
    ],
)
actions.add_sequence(
    "corruption_cube",
    [
        {"type": "key_press", "button": "7", "modifiers": [Key.shift]},
    ],
)
actions.add_sequence(
    "corruption_end",
    [
        {"type": "key_press", "button": "8", "modifiers": [Key.shift]},
    ],
)
actions.add_sequence(
    "corruption_reset",
    [
        {"type": "key_press", "button": "0", "modifiers": [Key.shift]},
    ],
)
actions.add_sequence(
    "toggle_challenges",
    [
        {"type": "key_press", "button": "c"},
    ],
)
actions.add_sequence(
    "exit_reincarnation_challenges",
    [
        {"type": "key_press", "button": "e"},
    ],
)
actions.add_sequence(
    "exit_ascension_challenges",
    [
        {"type": "key_press", "button": "e", "modifiers": [Key.shift]},
        {"type": "key_press", "button": "e"},
        {"type": "key_press", "button": "enter", "delay": 0.01},
        {"type": "key_press", "button": "enter", "delay": 0.01},
    ],
)
chall_delay = 0.25
actions.add_sequence(
    "pulse_challenges",
    [
        {"type": "key_press", "button": "0", "delay": chall_delay},
        {"type": "key_press", "button": "e", "delay": chall_delay},
        {"type": "key_press", "button": "1", "delay": chall_delay},
        {"type": "key_press", "button": "2", "delay": chall_delay},
        {"type": "key_press", "button": "3", "delay": chall_delay},
        {"type": "key_press", "button": "4", "delay": chall_delay},
        {"type": "key_press", "button": "5", "delay": chall_delay},
        {"type": "key_press", "button": "6", "delay": chall_delay},
        {"type": "key_press", "button": "7", "delay": chall_delay},
        {"type": "key_press", "button": "8", "delay": chall_delay},
        {"type": "key_press", "button": "9", "delay": chall_delay},
    ],
)
actions.add_sequence(
    "C10",
    [
        {"type": "key_press", "button": "0", "delay": chall_delay},
        {"type": "key_press", "button": "e", "delay": chall_delay},
    ],
)


def extract_numbers(text):
    # Regular expression pattern to match numbers with optional sign, commas, and decimal points
    pattern = r"[+-]?(\d{1,3}(,\d{3})*|\d+)(\.\d+)?"

    # Find all matches according to the regex pattern
    matches = re.findall(pattern, text)

    # Extract the full match strings
    numbers = [match[0] + match[2] for match in matches]

    # Clean and convert them to floats
    def to_float(number_str):
        # Remove commas for thousands separators
        number_str_cleaned = number_str.replace(",", "")
        # Convert to float
        return float(number_str_cleaned)

    float_numbers = [to_float(n) for n in numbers]
    return float_numbers


def basic_ambrosia_oct():
    pass


def check_ambrosia(default="max_cubes"):
    last_tab = STATE.get("CURRENT_TAB")

    if not STATE["AMBROSIA_LOADOUT"] or STATE["TIME_TO_LUCK"] <= 0:
        go_to_tab("singularity")
        actions.click("subtab:ambrosia")
        STATE["TIME_TO_LUCK"] = time_to_full_ambrosia_bar()
    remaining_time = STATE["TIME_TO_LUCK"] - time.time()

    changed_tab = False
    if 0 < remaining_time < 10:
        changed_tab = True
        go_to_tab("singularity")
        actions.click("subtab:ambrosia")
        actions.perform_sequence(f"ambrosia:loadout:max_luck")
        STATE["AMBROSIA_LOADOUT"] = "max_luck"
        time.sleep(remaining_time + 1)
        STATE["TIME_TO_LUCK"] = time_to_full_ambrosia_bar()
    if STATE["AMBROSIA_LOADOUT"] != default:
        changed_tab = True
        go_to_tab("singularity")
        loadout = default
        if default == "max_cubes" and STATE["P4x4"] < 1:
            loadout = "max_octeracts"
        actions.perform_sequence(f"ambrosia:loadout:{loadout}")
        STATE["AMBROSIA_LOADOUT"] = default

    if changed_tab:
        STATE["CURRENT_TAB"] = "singularity"
        go_to_tab(last_tab)
    go_to_tab("challenges")


def run_challenge(
    challenge,
    max_challenge=None,
    pulses=1,
    delay=None,
    c10_only=False,
    capture_completions=False,
    adds=0,
    ambrosia=False,
):
    if ambrosia:
        check_ambrosia()
    challenge_number = int(challenge[1:])
    if max_challenge is None:
        max_challenge = f"C{STATE['HIGHEST_BEATEN_CHALLENGE']}"
    actions.perform_sequence(f"challenge:{challenge}:highest_beaten:{max_challenge}")
    actions.perform_sequence(f"challenge:{challenge}:highest_beaten:{max_challenge}")
    if c10_only:
        actions.perform_sequence(f"challenge:C10:highest_beaten:{max_challenge}")
        actions.perform_sequence(f"challenge:C10:highest_beaten:{max_challenge}")
    else:
        for _ in range(pulses):
            actions.perform_sequence("pulse_challenges")
        if pulses:
            actions.perform_sequence("C10")
    if delay is not None:
        time.sleep(delay)

    completions = (0, 0)
    if capture_completions and challenge_number > 10:
        comps = get_completions(go_to=False)
        if comps:
            completions = comps[challenge_number - 11]
    elif capture_completions and challenge == "C10":
        actions.perform_sequence(
            f"challenge:{challenge}:highest_beaten:{max_challenge}:click"
        )
        if challenge == "C15":
            completions = get_completions()[-1]
        else:
            text = ocr.text_in_rectangle("challenges:completions")
            completions = (0, 0)
            for result in re.findall(r"(?P<completed>\d+)/(?P<total>\d+)", text):
                completions = tuple([int(x) for x in result])
                break
    if completions[0] > 0 and challenge_number > STATE["HIGHEST_BEATEN_CHALLENGE"]:
        if 9 < challenge_number < 15:
            STATE["HIGHEST_BEATEN_CHALLENGE"] = challenge_number

    if ambrosia and adds > 0:
        go_to_tab("singularity")
        actions.click(f"subtab:ambrosia")

        STATE["TIME_TO_LUCK"] = time_to_full_ambrosia_bar()
        actions.perform_sequence(f"ambrosia:loadout:max_quarks")
        for _ in range(adds):
            actions.perform_sequence("hotkey:add:x1")
            time.sleep(0.1)
        actions.perform_sequence(f"ambrosia:loadout:max_cubes")
        go_to_tab("challenges")
        actions.click(f"subtab:challenges_normal")

    if challenge_number == 10:
        actions.perform_sequence("hotkey:ascend")
    actions.perform_sequence("hotkey:exit_all_challenges")
    if ambrosia:
        check_ambrosia()

    return completions


def pre_C10_fast(C10=1):
    tries = 5
    while tries > 0:
        actions.perform_sequence(f"tab:challenges:C9")
        actions.perform_sequence(f"subtab:challenges_normal")
        actions.perform_sequence("pulse_challenges")
        actions.click("challenge:C10:highest_beaten:C9")
        actions.click("challenge:C10:highest_beaten:C9")
        time.sleep(0.1)
        actions.perform_sequence("hotkey:ascend")
        stage = approximate_stage()
        tries -= 1
        if stage == ":C9":
            continue
        break
    if tries < 0:
        raise ValueError("Could not perform a fast sing")


def pre_C15_fast(C10=1):
    tries = 5
    while tries > 0:
        actions.perform_sequence(f"tab:challenges:C10")
        actions.perform_sequence(f"subtab:challenges_normal")
        for challenge in [11, 12, 13, 14]:
            actions.click(f"challenge:C{challenge}:highest_beaten:C{challenge-1}")
            actions.click(f"challenge:C{challenge}:highest_beaten:C{challenge-1}")
            time.sleep(1)
            actions.click(f"challenge:C10:highest_beaten:C{challenge-1}")
            actions.click(f"challenge:C10:highest_beaten:C{challenge-1}")
            time.sleep(0.5)
            actions.perform_sequence("hotkey:ascend")
        actions.perform_sequence("hotkey:exit_all_challenges")
        stage = approximate_stage()
        tries -= 1
        if stage == "":
            break
    if tries < 0:
        raise ValueError("Could not perform a fast sing")


def pre_C10():
    go_to_tab("challenges", current=None)
    actions.click("subtab:challenges_normal")
    for i in range(20):
        go_to_tab("challenges")
        actions.click("subtab:challenges_normal")
        completions = None
        if i == -1:
            actions.perform_sequence("hotkey:autochallenge")
            time.sleep(10)
            actions.perform_sequence("hotkey:autochallenge")
            actions.perform_sequence("hotkey:ascend")
            comp = get_completions()
            if comp:
                completions = comp[0]
        else:
            completions = run_challenge(
                challenge="C10",
                delay=0.5,
                capture_completions=True,
                ambrosia=False,
            )
        if not completions:
            continue
        curr, _ = completions
        if curr < 0:
            continue
        actions.perform_sequence("hotkey:ascend")
        actions.perform_sequence("hotkey:ascend")
        stage = approximate_stage()
        if stage == ":C9":
            continue
        STATE["HIGHEST_BEATEN_CHALLENGE"] = 10
        return
    raise ValueError("Not able to reach C10!")


def get_completions(threshold=80, go_to=True):
    if go_to:
        go_to_tab("challenges")
    actions.click("subtab:challenges_normal")
    text = ocr.text_in_rectangle(
        "challenges:text_under_challenges",
        custom_config=r"--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789e/",
    )
    *parts, last = text.split()
    if "/" in last:
        parts.append(last)
        last = None
    formated = []
    for part in parts:
        if "/" not in part:
            continue
        try:
            curr, total = [float(x) for x in part.strip().split("/")]
        except ValueError:
            continue
        if total > threshold:
            continue
        formated.append([curr, total])
    if last is not None:
        formated.append([float(last), float("Inf")])
    STATE["HIGHEST_BEATEN_CHALLENGE"] = 9 + len(formated)
    return formated


def pre_C15(C15=1, delay=None, c13_delay=0.75):

    go_to_tab("challenges", current=None)
    actions.click(f"subtab:challenges_normal")

    challenges_current = {}
    challenges_maximum = {}
    for i in range(11, 15):
        challenges_current[f"C{i}"] = 0
        challenges_maximum[f"C{i}"] = 45

    count = -1
    while True:
        count += 1

        completions = get_completions()
        if not completions:
            go_to_buildings_tab()
            # go_to_tab("singularity")
            # STATE["TIME_TO_LUCK"] = time_to_full_ambrosia_bar()
            go_to_tab("challenges")
            actions.click(f"subtab:challenges_normal")
        for i, (curr, maximum) in enumerate(get_completions(), start=11):
            challenges_current[f"C{i}"] = curr
            challenges_maximum[f"C{i}"] = maximum

        if challenges_current.get("C14", 0) > 0:
            return

        sorted_by_name = sorted(challenges_current.items(), key=lambda x: int(x[0][1:]))
        sorted_by_least_completions = sorted(sorted_by_name, key=lambda x: x[1])
        print(sorted_by_least_completions)
        for challenge, completions in sorted_by_least_completions:
            challenge_number = int(challenge[1:])
            if completions and completions >= challenges_maximum.get(
                challenge, float("Inf")
            ):
                continue
            if not challenges_current.get(f"C{challenge_number-1}", float("inf")):
                continue

            ccs, max_ccs = run_challenge(
                challenge=challenge,
                c10_only=challenge == "C13",
                delay=c13_delay if challenge == "C13" else delay,
                capture_completions=True,
                ambrosia=True,
            )
            challenges_maximum[challenge] = max_ccs
            challenges_current[challenge] = ccs
            if ccs < 1:
                run_challenge(
                    challenge="C10",
                    pulses=2,
                    delay=delay,
                    ambrosia=True,
                )
                break
            print(
                f"{challenge=}", f"{ccs}/{max_ccs}", STATE["HIGHEST_BEATEN_CHALLENGE"]
            )
            if challenge == "C14":
                return
            # if int(challenge[1:]) > int(STATE['HIGHEST_BEATEN_CHALLENGE'][1:]):
            #    STATE["HIGHEST_BEATEN_CHALLENGE"] = challenge


def do_all_achievements():

    actions.perform_sequence("corruption_c14")
    actions.perform_sequence("challenge:C11:highest_beaten:C14")
    actions.perform_sequence("challenge:C11:highest_beaten:C14")
    actions.perform_sequence("pulse_challenges")
    actions.perform_sequence("hotkey:exit_challenge")

    # [42] Perfectly Respected: Prestige for at least 1e+250000 Diamonds.
    actions.perform_sequence("hotkey:prestige")

    # [49] Leaving the Universe: Transcend for at least 1e+100000 Mythos.
    actions.perform_sequence("hotkey:transcend")

    # [56] I Feel Luck in My Cells: Reincarnate for at least 1e+7777 Particles.
    actions.perform_sequence("hotkey:reincarnate")
    actions.perform_sequence("corruption_reset")
    actions.perform_sequence("hotkey:ascend")

    # [238] Three-folded: [Hint: you may want to look into the inception]
    actions.perform_sequence(f"challenge:C13:highest_beaten:C14")
    actions.perform_sequence(f"challenge:C13:highest_beaten:C14")
    actions.perform_sequence(f"challenge:C10:highest_beaten:C14")
    actions.perform_sequence(f"challenge:C10:highest_beaten:C14")
    actions.perform_sequence(f"challenge:C1:highest_beaten:C14")
    actions.perform_sequence("hotkey:exit_all_challenges")

    # [249] Overtaxed: [Hint: It might pay not to read!]
    actions.perform_sequence("corruption_reset")
    actions.perform_sequence(f"challenge:C13:highest_beaten:C14")
    actions.perform_sequence(f"challenge:C13:highest_beaten:C14")
    actions.perform_sequence("hotkey:autochallenge")

    # [246] Why? [Hint: Sometimes even 1 in over a Trillion counts!]
    go_to_tab("cubes")
    actions.perform_sequence("tributes:buy:x1")

    go_to_tab("settings")
    for code in [":unsmith:", ":antismith:"]:
        actions.perform_sequence("settings:promotion_code", input=code)
        time.sleep(0.1)
    check_ambrosia()
    go_to_tab("challenges")
    time.sleep(6)
    actions.perform_sequence("hotkey:autochallenge")

    # [248] Seeing Red but not Blue: [Hint: Can you get red stuff without getting blue stuff?]
    # actions.perform_sequence("challenge:C14:highest_beaten:C14")
    # actions.perform_sequence("challenge:C10:highest_beaten:C14")
    # actions.perform_sequence("click:antsac")
    # actions.perform_sequence("click:antsac")

    # actions.perform_sequence("challenge:C15:highest_beaten:C14")
    # actions.perform_sequence("pulse_challenges")


def time_to_full_ambrosia_bar():
    time_to_full = 0
    text = ocr.text_in_rectangle("ambrosia:blue_bar")
    try:
        current, total, per_second = extract_numbers(text)
        time_to_full = (total - current) / per_second
    except ValueError:
        pass
    return time_to_full + time.time()


def pre_aoag(
    C11=None, C12=None, C13=None, C14=None, C15=None, delay=None, c13_delay=0.75
):
    kwargs = {"C11": C11, "C12": C12, "C13": C13, "C14": C14, "C15": C15}
    targets = {c: t for (c, t) in kwargs.items() if t is not None}
    if all(target is None for target in targets.values()):
        raise ValueError("At least one of C11, C12, ..., C15 must be defined")
    challenges_current = {f"C{i}": 0.0 for i in range(11, 16)}
    challenges_maximum = {f"C{i}": 45.0 for i in range(11, 16)}
    count = -1

    go_to_tab("challenges")
    actions.click("subtab:challenges_normal")

    actions.click("challenge:C15:highest_beaten:C14")
    actions.click("challenge:C15:highest_beaten:C14")
    actions.perform_sequence("hotkey:autochallenge")
    completed_levels = get_completions(go_to=False)
    for i, (curr, maximum) in enumerate(completed_levels, start=1):
        challenge = f"C{i+10}"
        challenges_current[challenge] = curr
        challenges_maximum[challenge] = maximum

    if all(challenges_current.get(c, 0) >= t for c, t in targets.items()):
        return

    check_ambrosia()
    actions.perform_sequence("hotkey:autochallenge")
    while True:
        check_ambrosia()
        count += 1

        sorted_challenges = sorted(
            challenges_current.items(),
            key=lambda x: challenges_maximum[x[0]] - x[1],
            reverse=True,
        )
        for challenge, completions in sorted_challenges:
            if kwargs[challenge] == 0:
                continue
            elif completions >= challenges_maximum.get(challenge, float("Inf")):
                continue
            if challenge == "C15":
                actions.click("challenge:C15:highest_beaten:C14")
                actions.click("challenge:C15:highest_beaten:C14")
                actions.click("challenge:C10:highest_beaten:C14")
                actions.click("challenge:C10:highest_beaten:C14")
                actions.perform_sequence("hotkey:autochallenge")

                completed_levels = get_completions(go_to=False)
                for i, (curr, maximum) in enumerate(completed_levels, start=1):
                    challenge = f"C{i+10}"
                    challenges_current[challenge] = curr
                    challenges_maximum[challenge] = maximum
                actions.perform_sequence("hotkey:autochallenge")
                if all(challenges_current.get(c, 0) >= t for c, t in targets.items()):
                    return

            run_challenge(
                challenge=challenge,
                c10_only=challenge == "C13",
                delay=c13_delay if challenge == "C13" else delay,
                ambrosia=True,
            )

        if challenges_current["C15"] > float("1e20"):
            if count % 5 == 0:
                actions.perform_sequence("corruption_cube")
            else:
                actions.perform_sequence("corruption_p4x2")
        elif challenges_current["C15"] > float("1e16"):
            actions.perform_sequence("corruption_p3x1")
        elif challenges_current["C15"] > float("1e14"):
            actions.perform_sequence("corruption_p2x2max")
        elif challenges_current["C15"] > float("1e11"):
            actions.perform_sequence("corruption_w5x10max")
        elif challenges_current["C15"] > float("1e7"):
            actions.perform_sequence("corruption_preplat")
        else:
            actions.perform_sequence("corruption_c14")
        actions.perform_sequence("hotkey:ascend")

        completions = run_challenge(challenge="C10", pulses=2, delay=delay)

        actions.perform_sequence("corruption_c14")


# def pre_aoag(C15=float("1e40"):
#    while True:
#        challenges_current = {f"C{i}": 0.0 for i in range(11, 16)}
#        challenges_maximum = {f"C{i}": 45.0 for i in range(11, 16)}
#        c15_current = get_completions()[-1][0]
#
#        completions = run_challenge(challenge=challenge, max_challenge="C15")
#        for i in range(3):
#            actions.perform_sequence("pulse_challenges")


def post_aoag(C15=float("1e92")):

    # [248] Seeing Red but not Blue: [Hint: Can you get red stuff without getting blue stuff?]
    # actions.perform_sequence("challenge:C14:highest_beaten:C14")
    # actions.perform_sequence("challenge:C14:highest_beaten:C14")
    # actions.perform_sequence("challenge:C10:highest_beaten:C14")
    # actions.perform_sequence("challenge:C10:highest_beaten:C14")
    # actions.perform_sequence("hotkey:antsac")
    # actions.perform_sequence("hotkey:antsac")

    actions.perform_sequence("corruption_p4x2")
    actions.perform_sequence("hotkey:ascend")
    for k in range(7):
        check_ambrosia()
        run_challenge(
            challenge="C10",
            ambrosia=True,
            adds=1 if k > 3 else 0,
            delay=1,
        )
        actions.perform_sequence("challenge:C15:highest_beaten:C14")
        actions.perform_sequence("challenge:C15:highest_beaten:C14")
        actions.perform_sequence("pulse_challenges")
        actions.perform_sequence("challenge:C6:highest_beaten:C14")
        actions.perform_sequence("challenge:C6:highest_beaten:C14")
        for i in reversed(range(1, 6)):
            actions.perform_sequence(f"challenge:C{i}:highest_beaten:C14")
            actions.perform_sequence(f"challenge:C{i}:highest_beaten:C14")
        actions.perform_sequence(f"hotkey:exit_all_challenges")

    go_to_tab("singularity")
    actions.click(f"subtab:ambrosia")

    STATE["TIME_TO_LUCK"] = time_to_full_ambrosia_bar()
    actions.perform_sequence(f"ambrosia:loadout:max_quarks")
    actions.perform_sequence("hotkey:ascend")
    actions.perform_sequence(f"ambrosia:loadout:max_cubes")

    go_to_tab("challenges")
    actions.click(f"subtab:challenges_normal")


def get_gq_spent_on_upgrade(y, x):
    actions.hover(name=f"singularity_shop:s{y}x{x}")
    spent_text = ocr.text_in_rectangle("singularity_shop:spent_gq_on_upgrade")
    last_part = spent_text.split()[-1]
    spent_gq = float("0")
    try:
        spent_gq = float(last_part)
    except ValueError:
        base, power = extract_numbers(spent_text.split()[-1])
        spent_gq = float(f"{base}e{int(power)}")
    return spent_gq


def buy_singularity_upgrades(
    ascension_count=1,
    obtainium=1,
    offerings=1,
    cube=100,
    citadel=200,
    octeracts=1,
    bb_speed=True,
    luck=True,
    gq: Optional[int] = None,
):
    go_to_tab("singularity")
    actions.perform_sequence("subtab:singularity_shop")
    _kwargs: dict[str, dict[str, Any]] = {
        "ascension_count": {"ratio": ascension_count, "pos": (2, 5)},
        "obtainium": {"ratio": obtainium, "pos": (2, 12)},
        "offerings": {"ratio": offerings, "pos": (3, 1)},
        "cube_flame": {"ratio": cube, "pos": (3, 4)},
        "fake_citadel": {"ratio": citadel, "pos": (3, 7)},
        "octeract_absinthe": {"ratio": octeracts, "pos": (4, 7)},
    }
    kwargs = {k: v for (k, v) in _kwargs.items() if v["ratio"] > 0}
    for name, val in kwargs.items():
        kwargs[name]["spent"] = get_gq_spent_on_upgrade(*val["pos"])
    total_ratio = sum(v["ratio"] for v in kwargs.values())
    total_spent = sum(v["spent"] for v in kwargs.values())

    # for i in [4, 3]:
    #    if luck:
    #        actions.perform_sequence(f"singularity_shop:buy:ambrosia_luck_{i}:x1")
    #    if bb_speed:
    #        actions.perform_sequence(f"singularity_shop:buy:blueberry_speed_{i}:x1")
    # STATE["CURRENT_TAB"] = "singularity"

    gq_to_spend = float("0")
    if gq is not None:
        gq_to_spend = gq
    else:
        actions.perform_sequence("subtab:singularity_shop")
        text = ocr.text_in_rectangle("sing_shop:gq").lower()
        gq_to_spend = float("0")
        text = text.split("have", maxsplit=1)[1]
        text = text.split("golden", maxsplit=1)[0].strip()
        try:
            gq_to_spend = float(text)
        except ValueError:
            try:
                first, second = extract_numbers(text)
                gq_to_spend = float(f"{first}e{int(second)}")
            except ValueError:
                pass

    total_positive_defifiency = 0
    for name, val in kwargs.items():
        expect_gq_spent = (val["ratio"] / total_ratio) * (total_spent + gq_to_spend)
        deficiency = expect_gq_spent - val["spent"]
        kwargs[name]["deficiency"] = deficiency
        if deficiency >= 0:
            total_positive_defifiency += deficiency

    name_by_deficiency = sorted(
        (v["deficiency"], k) for (k, v) in kwargs.items() if v["deficiency"] > 0
    )
    for deficiency, name in name_by_deficiency:
        to_buy = "-1"
        if not (name == name_by_deficiency[-1][-1] and gq is None):
            to_buy = f"{gq_to_spend * (deficiency / total_positive_defifiency):2.2e}".replace(
                "+", ""
            )
        y, x = kwargs[name]["pos"]
        actions.perform_sequence(f"singularity_shop:buy:s{y}x{x}:custom", input=to_buy)

    actions.perform_sequence("subtab:singularity_shop")
    text = ocr.text_in_rectangle("sing_shop:gq").lower()
    text = text.split("have", maxsplit=1)[1]
    text = text.split("golden", maxsplit=1)[0].strip()

    gq_remaining = float("0")
    try:
        gq_remaining = float(text)
    except ValueError:
        try:
            first, second = extract_numbers(text)
            gq_to_spend = float(f"{first}e{int(second)}")
        except ValueError:
            pass
    return gq_to_spend - gq_remaining


def expand_qhept(quarks=-1, threshold=0.99):
    go_to_tab("cubes")
    actions.perform_sequence("subtab:forge")

    text = ocr.text_in_rectangle(
        "resources:quarks",
        custom_config=r"--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789e",
    ).strip()
    current_gq = 0
    try:
        current_gq = float(text.strip())
    except ValueError:
        try:
            first, second = extract_numbers(current_gq)
            current_gq = float(f"{float(first)}e{int(second)}")
        except ValueError:
            pass

    if quarks == -1:
        actions.perform_sequence("qhept:buy:max")
    elif quarks > 0:
        actions.perform_sequence("qhept:buy:custom", input="1")
    try:
        text = ocr.text_in_rectangle("qhept:bar").strip()
        nums = []
        for number in map(str.strip, text.split("/")):
            try:
                nums.append(float(number))
            except ValueError:
                first, second = extract_numbers(number)
                nums.append(float(f"{first}e{int(second)}"))
        current, maximum = nums
        percentage = current / maximum
        if percentage > threshold:
            actions.perform_sequence("qhept:expand")
    except ValueError:
        pass

    remaining_gq = 0
    if current_gq > 0:
        text = ocr.text_in_rectangle(
            "resources:quarks",
            custom_config=r"--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789e",
        )
        try:
            remaining_gq = float(text.strip())
        except ValueError:
            try:
                first, second = extract_numbers(current_gq)
                current_gq = float(f"{float(first)}e{int(second)}")
            except ValueError:
                pass
    return max(current_gq - remaining_gq, 0.0)


def repeat_sing(
    times=0, stage=None, spend_gq_last_sing=False, spend_quarks_last_sing=False
):

    # check_ambrosia()

    # for _ in range(5):
    #    actions.perform_sequence("hotkey:enter")
    # if stage is None:
    #    stage = approximate_stage()
    longest_sing_time = 600

    STATE["P4x4"] = 0
    if stage == "post_aoag":
        STATE["P4x4"] = 40

    while True:
        for _ in range(5):
            actions.perform_sequence("hotkey:enter")
        current_time = int(time.time())
        if (
            STATE["SING_STARTED_AT"]
            and current_time - STATE["SING_STARTED_AT"] > longest_sing_time
        ):
            raise ValueError("too long sing, must recalculate!")
        if stage == "post_aoag":
            if STATE["SINGS"] > 0:
                reset_current_sing()
                STATE["P4x4"] = 0
                STATE["AMBROSIA_LOADOUT"] = ""
                STATE["TIME_TO_LUCK"] = 0
                STATE["HIGHEST_BEATEN_CHALLENGE"] = 9
                STATE["CURRENT_TAB"] = ""
                stage = approximate_stage()
                check_ambrosia()
                STATE["TIME_TO_SING"] = current_time - STATE["SING_STARTED_AT"]
                STATE["SING_STARTED_AT"] = current_time
            if STATE["TIME_TO_SING"] > 0:
                STATE["GQ_PER_HOUR"] = 3600 * (
                    STATE["GQ_SPENT_LAST_SING"] / STATE["TIME_TO_SING"]
                )
                STATE["QUARKS_PER_HOUR"] = 3600 * (
                    STATE["QUARKS_SPENT_LAST_SING"] / STATE["TIME_TO_SING"]
                )
            if STATE["SINGS"] > 0:
                pprint(STATE)
        else:
            STATE["SING_STARTED_AT"] = current_time
        if stage == "pre_C10":
            pre_C10()
            stage = "pre_C15"
        if stage == "pre_C15":
            pre_C15()
            stage = "pre_aoag"
        if stage == "pre_aoag":
            # do_all_achievements()
            pre_aoag(
                C15=float("1e20"),
            )
            STATE["AMBROSIA_LOADOUT"] = ""
            STATE["P4x4"] = 40
            check_ambrosia()
            pre_aoag(
                C11=float("70"),
                C12=float("70"),
                C14=float("70"),
                C13=float("70"),
            )
            stage = "post_aoag"
        if stage == "post_aoag":
            post_aoag()
            check_ambrosia()

            STATE["SINGS"] += 1
            if STATE["SINGS"] > times and times != -1:
                break

            STATE["GQ_SPENT_LAST_SING"] = buy_singularity_upgrades()
            STATE["GQ_SPENT"] += STATE["GQ_SPENT_LAST_SING"]
            check_ambrosia()

            go_to_tab("settings")
            actions.click("subtab:settings")
            actions.perform_sequence("settings:daily")

            go_to_tab("shop")
            # actions.perform_sequence("quark_shop:buy:s1x5:custom", input=1)
            actions.perform_sequence("quark_shop:buy:s1x6:custom", input=1)

            STATE["QUARKS_SPENT_LAST_SING"] = expand_qhept(quarks=-1)
            STATE["QUARKS_SPENT"] += STATE["QUARKS_SPENT_LAST_SING"]
            check_ambrosia()

            pprint(STATE)

    if spend_gq_last_sing:
        STATE["GQ_SPENT_LAST_SING"] = buy_singularity_upgrades()
        STATE["GQ_SPENT"] += STATE["GQ_SPENT_LAST_SING"]
    if spend_quarks_last_sing:
        STATE["QUARKS_SPENT_LAST_SING"] = expand_qhept(quarks=-1)
        STATE["QUARKS_SPENT"] += STATE["QUARKS_SPENT_LAST_SING"]
    pprint(STATE)


def go_to_buildings_tab():
    current_stage = None
    for stage in ["", ":C10", ":C9"]:
        actions.perform_sequence(f"tab:buildings{stage}")
        actions.perform_sequence("subtab:buildings:coin")
        text = ocr.text_in_rectangle("buildings:coin:workers").lower()
        if "workers" in text:
            current_stage = stage
            break
    if current_stage is not None:
        STATE["CURRENT_TAB"] = "buildings"
        return current_stage


def approximate_stage():
    current_stage = go_to_buildings_tab()
    if current_stage is None:
        raise ValueError("Unable to determine stage!")
    for _ in range(4):
        actions.perform_sequence("hotkey:tab:next")
    STATE["CURRENT_TAB"] = "challenges"
    completions = get_completions(go_to=False)
    if completions:
        STATE["HIGHEST_BEATEN_CHALLENGE"] = 10 + (len(completions) - 1)
    else:
        STATE["HIGHEST_BEATEN_CHALLENGE"] = 9
    if STATE["HIGHEST_BEATEN_CHALLENGE"] < 14:
        return "pre_C15"
    if completions[-1][0] > float("1e40"):
        return "post_aoag"
    return "pre_aoag"


def main():

    # Define a sequence of actions with named rectangles
    # go_to_tab("challenges")
    # pre_C15()
    # upgrade = SingularityUpgrade(
    #    "Golden Quarks I",
    #    1,
    #    level=34,
    #    free_level=174.26,
    #    max_level=34,
    #    effect_formula=lambda n: (1 + 0.1 * n),
    # )
    # cost = upgrade.get_cost_tnl()
    # yield_spread(three_to_sevens=1, eights=100)
    # spread, gq_remaining = optimize_upgrade_spread(
    #    current_flame_level=2_483_412,
    #    current_citadel_level=75_237,
    #    current_absinthe_level=147_087,
    #    gq=float("6.19e20"),
    #    free_flame_levels= 10_000,
    #    free_citadel_levels= 100,
    #    free_absinthe_levels= 0,
    # )
    # pprint(spread)
    # pprint(f"{gq_remaining:2.2f}")
    # amb = Ambrosia()
    # luck_base = 1501
    # luck_so_far = luck_base
    # luck_multiplier = 12 / 100
    # ambrosia = 952835
    # quarks = float("2.29e18")
    # luck_1 = amb._ambrosia_upgrades["ambrosiaLuck1"]
    # luck_so_far += luck_1.luck(24)
    # luck_quark = amb._ambrosia_upgrades["ambrosiaLuckQuark1"]
    # cube_quark = amb._ambrosia_upgrades["ambrosiaCubeQuark1"]
    # luck = (luck_base + luck_1.luck(24)) * (1 + luck_multiplier)
    # p4x4 = 50

    # stats = load_stats()
    # print(stats)

    # best_cube_loadout_exact = amb.calculate(
    #    ooms = stats["ooms"],
    #    loadout="cubes",
    #    ambrosia=ambrosia,
    #    quarks=stats["quarks"],
    #    luck_base=luck_base,
    #    luck_mult=luck_multiplier,
    #    p4x4=0,
    #    use_preboughts=True,
    # )
    # best_cube_loadout_exact = {
    #    "ambrosiaTutorial": 10,
    #    "ambrosiaLuck1": 61,
    #    "ambrosiaCubes1": 20,
    #    "ambrosiaQuarks1": 20,
    #    "ambrosiaQuarkLuck1": 13,
    #    "ambrosiaCubeLuck1": 13,
    #    "ambrosiaLuck2": 22,
    # }
    # costs = {name: amb._ambrosia_upgrades[name].cumulative_cost(level) for name, level in best_cube_loadout_exact.items()}
    # print(best_cube_loadout_exact)
    # pprint(costs)
    # print(sum(costs.values()))
    # bonuses = amb.calculate_bonus(
    #    best_cube_loadout_exact,
    #    luck_base=luck_base,
    #    luck_mult=luck_multiplier,
    #    quarks=quarks,
    #    ooms=stats["ooms"],
    #    p4x4=p4x4,
    # )
    # print(best_cube_loadout_exact)
    # for name, bonus in bonuses.items():
    #    if name == "luck":
    #        print(f"{name+':':<10} {bonus:,.2f}")
    #    else:
    #        print(f"{name+':':<10} {(100 * (bonus - 1)):,.2f}%")

    # for i in range(20):
    #    ambrosia = 100_000 * i
    #    best_cube_loadout_exact, cube_bonus = amb.calculate(
    #        "cubes",
    #        ambrosia=ambrosia,
    #        quarks=(i+1)*quarks,
    #        luck_base=i/10*luck_base,
    #        luck_mult=i/50*luck_multiplier,
    #        use_preboughts=True,
    #    )
    #    print(ambrosia, best_cube_loadout_exact, f"{int(100 * (cube_bonus - 1))}%")
    #    spent = 0
    #    for name, levels in best_cube_loadout_exact.items():
    #        upgrade = amb._ambrosia_upgrades[name]
    #        spent += upgrade.cumulative_cost(levels)
    #    print(spent, ambrosia)
    # return

    # go_to_buildings_tab()
    # go_to_tab("settings")
    # stats = load_stats()
    # pprint(stats)

    # actions.click("subtab:stats_for_nerds")
    # actions.click("stats_for_nerds:savefile:1")
    # actions.click("stats_for_nerds:savefile:2")

    # upgrades = {
    #    "Citadel of Singularity": SingularityUpgrade(
    #        "Citadel of Singularity",
    #        500000,
    #        free_level=free_citadel_levels,
    #        level=0,
    #        effect_formula=lambda n: (1 + 0.02 * n) * (1 + (n // 10) / 100),
    #    ),
    #    "Cube Flame": SingularityUpgrade(
    #        "Cube Flame",
    #        1,
    #        free_level=free_cube_flame_levels,
    #        level=0,
    #        effect_formula=lambda n: 1 + 0.01 * n,
    #    ),
    #    "Octeract Absinthe": SingularityUpgrade(
    #        "Octeract Absinthe",
    #        20000,
    #        free_level=free_absinthe_levels,
    #        level=0,
    #        effect_formula=lambda n: 1 + 0.0125 * n,
    #    ),
    # }
    # cumsum = 0
    # cost = 0
    # cube_flame = SingularityUpgrade(
    #        "Cube Flame",
    #        1,
    #        free_level=5000,
    #        level=0,
    #        effect_formula=lambda n: 1 + 0.01 * n,
    #    )
    # print(f"Cube Flame: level: {cube_flame.level}, {cost=}, {cumsum=}")
    # levels = 5600
    # start = 0
    # cube_flame.level = start
    # for _ in range(start,start+levels+1):
    #    cost = cube_flame.get_cost_tnl()
    #    cumsum += cost
    #    cube_flame.level += 1
    #    print(f"Cube Flame: level: {cube_flame.level}, {cost=}, {cumsum=}")
    # return

    # time.sleep(1)
    # actions.perform_sequence("hotkey:enter")
    # time.sleep(1)

    # print(optimize_upgrade_spread_by_product(gq=float("1e22")))

    # citadel = SingularityUpgrade(
    #    "Citadel of Singularity",
    #    500000,
    #    level=83627,
    #    free_level=100,
    #    effect_formula=lambda n: (1 + 0.02 * n) * (1 + (n // 10) / 100),
    # )
    # print(f"Citadel effect: {100*(citadel.effect()-1):2.2e}%")
    # print(f"{citadel.get_cost_tnl():2.2e}")
    # return

    upgrades_affecting_cubes = ["Cube Flame", "Citadel of Singularity"]
    upgrades_affecting_octeracts = ["Cube Flame", "Octeract Absinthe"]
    names = ["flame_ratio", "citadel_ratio", "octeract_ratio"]
    ratios = [(1, 1, 1), (29, 21, 14), (1, 1, 0.65)]
    # free_flame = 100_000
    # gq=float("1e21")
    # print("="*79)
    # print(f'"GQ": {gq}, "Cube Flame": {free_flame}')
    # print("="*79)
    # flame_ratio = 1
    # citadel_ratio = 1
    # best_product = 0
    # for j in range(200,230):
    #    citadel_ratio=j/100
    #    for k in [0]:
    #        octeract_ratio=k/100
    #        results = singularity_purchases(
    #                    gq=gq,
    #                    flame_ratio=1,
    #                    citadel_ratio=citadel_ratio,
    #                    octeract_ratio=octeract_ratio,
    #                    free_flame_levels=free_flame,
    #                )
    #        multiplier_cubes = math.prod(v.get("cubes", 1) for v in results.values())
    #        multiplier_octeracts = math.prod(v.get("octeracts", 1) for v in results.values())
    #        levels = [f"{name}: {c['level']}" for (name, c) in results.items()]
    #        product = multiplier_cubes * multiplier_octeracts
    #        product = multiplier_cubes
    #        if product > best_product:
    #            best_product=product
    #            print(f"{'Ratios:':<10} {(flame_ratio, citadel_ratio, octeract_ratio)}")
    #            print(f"{'Octeracts:':<10} {100*(1 * multiplier_octeracts-1):2.2e}%")
    #            print(f"{'Cubes:':<10} {100*(multiplier_cubes * 1-1):2.2e}%")
    #            print(f"{'Product:':<10} {100*(product-1):2.2e}%")
    #            print(", ".join(levels))
    #            print("="*79)

    # naive_optimizer_singularity(free_cube_flame_levels=100_000)

    # {"ambrosiaTutorial":10,"ambrosiaPatreon":1,"ambrosiaHyperflux":5,"ambrosiaQuarks1":20,"ambrosiaCubes1":50,"ambrosiaLuck1":20,"ambrosiaLuckCube1":7,"ambrosiaQuarkCube1":7,"ambrosiaCubes2":15}

    # =================
    #   AUTOSINGER
    # =================
    for _ in range(5):
        actions.perform_sequence("hotkey:enter")
    stage = approximate_stage()
    for _ in range(10):
        try:
            repeat_sing(times=-1, stage=stage)
            break
        except ValueError as e:
            for _ in range(5):
                actions.perform_sequence("hotkey:enter")
            STATE["TIME_TO_SING"] = 0
            STATE["CURRENT_TAB"] = ""
            STATE["AMBROSIA_LOADOUT"] = ""
            stage = approximate_stage()
            STATE["TIME_TO_SING"] = 40 if stage == "post_aoag" else 0
            print(f"Error: {e}")
    return

    # y,x=3,4
    # actions.hover(name=f"singularity_shop:s{y}x{x}")
    # ocr.text_in_rectangle("tab:singularity")

    # ocr.text_in_rectangle("challenge:C1:highest_beaten:C9")

    # actions.perform_sequence("challenge:C1:highest_beaten:C14")
    # actions.click("tab:settings")
    # rectangle_settings = geometry.get_rectangle("tab:settings")
    # print(rectangle_settings)
    # print(ocr.text_in_rectangle("stats_for_nerds:savefile"))

    # actions.click("subtab:stats_for_nerds")
    # buy_singularity_upgrades()

    # time.sleep(1)
    # actions.perform_sequence("tab:challenges:C9")
    # go_to_tab("challenges")
    # check_ambrosia()
    # pre_C10()
    # pre_C15()
    # pre_aoag(
    #    C11=float("70"),
    #    C12=float("70"),
    #    C14=float("70"),
    #    C13=float("70"),
    #    C15=float("1e70"),
    # )
    # STATE['HIGHEST_BEATEN_CHALLENGE']=10
    # actions.perform_sequence(f"tab:challenges{c()}")
    # time_to_full_ambrosia_bar()
    # actions.perform_sequence("challenge:C10:highest_beaten:C10")
    # actions.perform_sequence("tab:buildings:C10")

    # post_aoag()

    # completions = run_challenge(
    #    challenge="C10",
    #    delay=3,
    #    capture_completions=True,
    #    adds=1,
    #    ambrosia=True,
    # )
    # print(completions)
    # actions.perform_sequence("challenge:C11:highest_beaten:C11")
    # repeat_sing(times=1)

    #ambrosia = Ambrosia()
    #quarks = float("2.29e18")
    #luck_base = 1604
    #luck_multiplier = 12/100
    #ambrosia_amount = 995703

    #stats = load_stats()
    #print("NO QUARKS, NO P4x4")

    #best_loadout = ambrosia.calculate(
    #    "cubes",
    #    ambrosia=ambrosia_amount,
    #    quarks=float("1e11"),
    #    luck_base=luck_base,
    #    luck_mult=luck_multiplier,
    #    ooms=100,
    #    p4x4=0,
    #)
    #bonus = ambrosia.calculate_bonus(
    #    loadout=best_loadout,
    #    quarks=stats["quarks"],
    #    ooms=stats["ooms"],
    #    luck_base=luck_base,
    #    luck_mult=luck_multiplier,
    #    p4x4=0,
    #)

    #print("MAXED")
    #print(stats)
    name = "cubes"
    #for name in ["luck"]:
    #    best_loadout = ambrosia.calculate(
    #        name,
    #        ambrosia=ambrosia_amount,
    #        quarks=stats["quarks"],
    #        luck_base=luck_base,
    #        luck_mult=luck_multiplier,
    #        ooms=stats["ooms"],
    #        p4x4=40,
    #    )
    #    bonus = ambrosia.calculate_bonus(
    #        loadout=best_loadout,
    #        quarks=stats["quarks"],
    #        ooms=stats["ooms"],
    #        luck_base=luck_base,
    #        luck_mult=luck_multiplier,
    #        p4x4=40,
    #    )
    #    with open(Path.home() / "Downloads" / f"post_aoag_{name}", "w") as f:
    #        f.write(json.dumps(best_loadout))
    #    print(name, json.dumps(best_loadout))
    #    print(bonus)


    #start=time.time()

    #best_loadout = ambrosia.best_luck_loadout_greedy(
    #    ambrosia=ambrosia_amount,
    #    quarks=stats["quarks"],
    #    luck_base=luck_base,
    #    luck_mult=luck_multiplier,
    #    ooms=stats["ooms"],
    #)
    #bonus = ambrosia.calculate_bonus(
    #    loadout=best_loadout,
    #    quarks=stats["quarks"],
    #    ooms=stats["ooms"],
    #    luck_base=luck_base,
    #    luck_mult=luck_multiplier,
    #    p4x4=40,
    #)
    #print(f"TIME: {time.time() - start}")
    #print(best_loadout)
    #print(bonus)

    # Level 6/25
    # This first generation hybrid module increases cube gain by 112.19%
    return
    # actions.perform_sequence("reset_current_sing")
    # actions.perform_sequence("challenges:C11:highest_beaten:C11")
    # actions.perform_sequence("toggle_challenges")
    # time.sleep(10)
    # actions.perform_sequence()
    # time.sleep(10)
    # actions.perform_sequence("challenge_C11_first_time")
    # time.sleep(30)
    # for _ in range(3):
    #    actions.perform_sequence("corruption_c14")
    #    actions.perform_sequence("exit_ascension_challenge")
    #    time.sleep(15)
    #    actions.perform_sequence("corruption_reset")
    #    actions.perform_sequence("challenge_c15")
    #    time.sleep(5)
    #    actions.perform_sequence("challenge_c11")
    #    time.sleep(10)
    # actions.perform_sequence("challenge_c11")
    # time.sleep(45)
    # for _ in range(6):
    #    actions.perform_sequence("corruption_p4x1")
    #    actions.perform_sequence("exit_ascension_challenge")
    #    time.sleep(20)
    #    actions.perform_sequence("corruption_reset")
    #    actions.perform_sequence("challenge_c15")
    #    time.sleep(5)

    ## Max C13 and the challenges
    # actions.perform_sequence("corruption_reset")
    # actions.perform_sequence("challenge_c11")
    # time.sleep(30)
    # actions.perform_sequence("exit_ascension_challenge")

    # actions.perform_sequence("corruption_end")
    # for _ in range(6):
    #    actions.perform_sequence("challenge_c11")
    #    time.sleep(20)
    # actions.perform_sequence("exit_ascension_challenge")
    # actions.perform_sequence("corruption_p4x1")
    # actions.perform_sequence("exit_ascension_challenge")

    # text = ocr.text_in_rectangle("ambrosia:blue_bar")
    # current, total, per_second = extract_numbers(text)
    # time_to_full = (total-current)/per_second
    # while True:
    #    time.sleep(wait:=int(time_to_full)-4)
    #    time_to_full -= wait
    #    actions.perform_sequence("ambrosia:loadout:max_luck")
    #    time.sleep(int(1+time_to_full)+3)
    #    actions.perform_sequence("ambrosia:loadout:max_octeract")
    #    text = ocr.text_in_rectangle("ambrosia:blue_bar"deficiency / total_positive_defifiency)
    #    current, total, per_second = extract_numbers(text)
    #    time_to_full = (total-current)/per_second
    #    print(time_to_full)

    # actions.perform_sequence("buy_cube_flame", input='10')

    # Set new dimensions for scaling
    # base_shop = geometry.get_rectangle("shop")  # Original dimensions
    # new_shop = Rectangle("shop", 60, 120, 150, 100)  # New dimensions

    # Set scaling based on new dimensions
    # geometry.set_scaling(base_shop, new_shop)

    # Perform the sequence with the new scaling applied
    # actions.perform_sequence('buy_apples_sequence')
