import matplotlib.pyplot as plt
import numpy as np


class Compliance:
    def __init__(self, min, recommended, max_bonus, start_of_penalty, end_of_penalty=None):
        # start_of_penalty is the first unit or session where penalty is > 0. This should be taken into account
        # when calculating the points using np.interp or when plotting the points.
        if end_of_penalty is None:
            end_of_penalty = start_of_penalty if recommended == max_bonus \
                else start_of_penalty - 1 + 2*(max_bonus - recommended)

        end_of_penalty = start_of_penalty - 1 + max_bonus if end_of_penalty is None else end_of_penalty
        self.params = [min, recommended, max_bonus, start_of_penalty - 1, end_of_penalty]

    def min(self):
        return self.params[0]

    def recommended(self):
        return self.params[1]

    def max_bonus(self):
        return self.params[2]

    def start_of_penalty(self):
        return self.params[3] + 1

    def end_of_penalty(self):
        return self.params[-1]


class Score:
    SORTED = "sorted"
    ACCUMULATED = "accumulated"

    SINGLE_SESSION = Compliance(1, 1, 1, 1)

    FIGSIZE = (6, 2)

    def __init__(self, units, sessions=SINGLE_SESSION, description=None, unit_description=None):
        self.units = units
        self.sessions = sessions
        if self.sessions.recommended() > 0:
            max_score = 100.0 / self.sessions.recommended()
            min_score = max_score * self.units.min() / self.units.recommended() if self.units.recommended() > 0 else max_score
        else:
            max_score = min_score = 100
        self.score = [min_score, max_score, 2 * max_score, 2 * max_score, 0]
        self.description = "" if description is None else description
        self.unit_description = unit_description

    def _get_score(self, session_units):
        return 0 if session_units < self.units.min() else np.interp(session_units, self.units.params, self.score)

    def get_session_score(self, session_units):
        if isinstance(session_units, list):
            return [self._get_score(d) for d in session_units]
        else:
            return self._get_score(session_units)

    def _plot(self):
        x = [0, self.units.min()] + self.units.params
        y = [0, 0] + self.score
        c = 'green'

        plt.figure(figsize=Score.FIGSIZE)
        plt.plot(x, y, linestyle='dashed', color=c)
        plt.ylabel('score')
        plt.title(f'{self.description} [units]')
        plt.xlabel('units' if self.unit_description is None else self.unit_description)
        return self

    @staticmethod
    def _to_list(v):
        return v if isinstance(v, list) else [v]

    def plot_units(self, show_lines=False):
        self._plot()
        if show_lines:
            for (d, score) in zip(self.units.params, self.score):
                plt.hlines(score, 0, d, color='green', linestyles='dotted')
                plt.vlines(d, 0, score, color='green', linestyles='dotted')
        plt.show()

    def plot_sessions(self, show_lines=False):
        self._fail_if_single_session()

        x = range(self.sessions.params[-1] + 1)
        y = [np.interp(i, self.sessions.params[-2:], [1, 0]) for i in x]
        c = 'red'
        plt.scatter(x, y, color='red', marker='s')
        if show_lines:
            for (s, m) in zip(x, y):
                # plt.hlines(score, 0, d, color=c, linestyles='dotted')
                if (m > 0):
                    plt.vlines(s, 0, m, color=c, linestyles='dotted')

        plt.title(f'{self.description} [sessions]')
        plt.show()

    def get_total_score(self, session_units):
        self._fail_if_single_session()

        session_units = self._to_list(session_units)
        num_sessions = len(session_units)

        if num_sessions < self.sessions.min():
            session_scores = accumulated_scores = [0]
        else:
            session_scores = np.array(self.get_session_score(session_units))

            # Sort session scores in descending order
            session_scores = -np.sort(-session_scores)

            # Calculate accumulated scores with the cutoff of 200%
            accumulated_scores = np.minimum(200, np.cumsum([session_scores[i] if i < self.sessions.max_bonus() else 0
                                                            for i in range(num_sessions)]))

            if len(accumulated_scores) >= self.sessions.start_of_penalty():
                penalty_sessions = self.sessions.params[-2:]
                penalty_scores = [0, accumulated_scores[self.sessions.max_bonus()]]

                # Correct accumulated scores
                accumulated_scores = np.maximum(0, [
                    accumulated_scores[i] - np.interp(i + 1, penalty_sessions, penalty_scores)
                    for i in range(num_sessions)])

        return {Score.SORTED: session_scores, Score.ACCUMULATED: accumulated_scores}

    def plot_session_score(self, session_units, show_labels=True):
        session_units = self._to_list(session_units)
        self._plot()

        many_sessions = len(session_units) > 1
        for (i, u) in enumerate(session_units):
            score = self._get_score(u)
            symbol = 'go' if score >= 0 else 'ro'
            # print(f"u = {u} s = {score:.2f}")
            plt.hlines(score, 0, u, color='green', linestyles='dotted')
            plt.vlines(u, 0, score, color='green', linestyles='dotted')
            plt.plot(u, score, symbol)
            if show_labels:
                label = f"(u = {u} s = {score:.2f})"
                plt.text(u, score + 2, label)
        plt.show()

    def plot_total_score(self, session_units):
        self._fail_if_single_session()

        session_units = self._to_list(session_units)
        total_score = self.get_total_score(session_units)

        x = np.arange(len(session_units))
        ticks = x + 1
        plt.figure(figsize=Score.FIGSIZE)
        plt.bar(x - 0.2, total_score[Score.SORTED], 0.4, label="session")
        plt.bar(x + 0.2, total_score[Score.ACCUMULATED], 0.4, label="accumulated")
        plt.xticks(x, ticks)
        plt.xlabel("session")
        plt.ylabel("score")
        plt.legend()
        plt.title(f"{self.description} - final score = {total_score[Score.ACCUMULATED][-1]}")
        plt.show()

    def plot_score(self):
        self.plot_session_score(list(self.duration))

    def print_total_score(self, session_units):
        self._fail_if_single_session()

        session_units = self._to_list(session_units)
        print(f"Session score     = {self.get_session_score(session_units)}")
        total_score = self.get_total_score(session_units)
        print(f"Sorted score      = {total_score[Score.SORTED]}")
        print(f"Accumulated score = {total_score[Score.ACCUMULATED]}")

    def print_session_score(self, session_units):
        session_units = self._to_list(session_units)
        print(f"Session score     = {self.get_session_score(session_units)}")

    def _fail_if_single_session(self):
        if self.sessions is Score.SINGLE_SESSION:
            raise Exception("Not supported for a single-session reward score")
