//#include <Windows.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <iostream>
#include <tuple>
#include <thread>
#include <queue>
#include <algorithm>

namespace py = pybind11;

struct WordScore
{
    int index{};
    double score{};

    bool operator<(const WordScore& rhs) const
    {
        return score < rhs.score;
    }
};

class WeightDamLeven
{

private:
    std::vector<std::vector<int>> m_keys_encoded;
    std::vector<std::vector<double>> m_cost_matrix;
    bool m_is_key_cost;
    double m_replace_cost;
    double m_insert_cost;
    double m_append_cost;
    double m_delete_cost;
    double m_transpose_cost;

public:
    WeightDamLeven(
        std::vector<std::vector<int>>& keys_encoded,
        std::vector<std::vector<double>>& cost_matrix,
        bool is_key_cost,
        double replace_cost, /* if is_key_cost, then this value is used when a key is out of cost_matrix */
        double insert_cost,
        double append_cost,
        double delete_cost,
        double transpose_cost)
    {
        m_keys_encoded = std::move(keys_encoded);
        m_cost_matrix = std::move(cost_matrix);
        m_is_key_cost = is_key_cost;
        m_replace_cost = replace_cost;
        m_insert_cost = insert_cost;
        m_append_cost = append_cost;
        m_delete_cost = delete_cost;
        m_transpose_cost = transpose_cost;
    }

    double key_weighted_damerau_levenshtein(
        const std::vector<int>& str1,
        const std::vector<int>& str2,
        const double score_to_beat)
    {
        int len1 = (int)str1.size();
        int len2 = (int)str2.size();

        // 3-row dynamic programming - only rows i, i-1, i-2 are needed
        // thread_local buffers - reused across calls, eliminates heap allocation in steady state
        thread_local std::vector<double> row0, row1, row2;
        std::vector<double>* rows[3] = { &row0, &row1, &row2 };
        for (auto* r : rows)
        {
            if ((int)r->size() < len2 + 1)
            {
                r->resize(len2 + 1);
            }
        }

        // p1 = row i-1 index, p2 = row i-2 index, cur = row being written
        int cur = 2;
        int p1 = 0;
        int p2 = 1;

        // initialize row 0 into rows[p1]
        (*rows[p1])[0] = 0.0;
        for (int j = 1; j <= len2; ++j)
        {
            double insert_append_cost = j > len1 ? m_append_cost : m_insert_cost;
            (*rows[p1])[j] = (*rows[p1])[j - 1] + insert_append_cost;
        }

        for (int i = 1; i <= len1; ++i)
        {
            // reset column 0 so that (*rows[cur])[j - 1] works when j == 1
            (*rows[cur])[0] = i * m_delete_cost;

            double best_score_this_row = (*rows[cur])[0];

            for (int j = 1; j <= len2; ++j)
            {
                int str1_idx = str1[i - 1];
                int str2_idx = str2[j - 1];

                double replace_cost_curr;
                if (str1_idx == str2_idx)
                {
                    replace_cost_curr = 0.0;
                }
                else if (m_is_key_cost)
                {
                    replace_cost_curr = m_replace_cost;
                    if (str1_idx < (int)m_cost_matrix.size() && str2_idx < (int)m_cost_matrix.size())
                    {
                        replace_cost_curr = m_cost_matrix[str1_idx][str2_idx];
                    }
                }
                else
                {
                    replace_cost_curr = m_replace_cost;
                }

                double insert_append_cost = j > len1 ? m_append_cost : m_insert_cost;
                (*rows[cur])[j] = std::min(
                    (*rows[p1])[j] + m_delete_cost, // delete
                    (*rows[cur])[j - 1] + insert_append_cost); // insert
                (*rows[cur])[j] = std::min(
                    (*rows[cur])[j],
                    (*rows[p1])[j - 1] + replace_cost_curr); // replace

                if (i > 1 && j > 1 && str1_idx == str2[j - 2] && str1[i - 2] == str2_idx)
                {
                    (*rows[cur])[j] = std::min(
                        (*rows[cur])[j],
                        (*rows[p2])[j - 2] + m_transpose_cost); // transpose
                }

                best_score_this_row = std::min(best_score_this_row, (*rows[cur])[j]);
            }

            if (score_to_beat >= 0 && best_score_this_row >= score_to_beat)
            {
                return score_to_beat + 1.0;
            }

            // recall p1 = row i-1 index, p2 = row i-2 index, cur = row being written
            // rotate: p2 -> p1; p1 -> cur; cur (recycled) -> p2 (oldest)
            // so p2 and p1 move up one index, and cur just uses the old p2 space
            int tmp = p2;
            p2 = p1;
            p1 = cur;
            cur = tmp;
        }

        return (*rows[p1])[len2]; // p1 holds the last written row after the final rotate
    }

    std::vector<std::tuple<std::vector<int>, double>> sort_word_scores(
        std::priority_queue<WordScore, std::vector<WordScore>>& heap)
    {
        // pop max-heap: results come out in descending score order
        std::vector<WordScore> word_scores;
        word_scores.reserve(heap.size());
        while (!heap.empty())
        {
            word_scores.push_back(heap.top());
            heap.pop();
        }
        // reverse to get ascending (best-first) order
        std::reverse(word_scores.begin(), word_scores.end());

        // convert to the return type: vector of tuples for Python
        std::vector<std::tuple<std::vector<int>, double>> result(word_scores.size());
        for (size_t i = 0; i < word_scores.size(); ++i)
        {
            result[i] = {m_keys_encoded[word_scores[i].index], word_scores[i].score};
        }
        return result;
    }

    void populate_heap(
        std::priority_queue<WordScore, std::vector<WordScore>>& heap,
        const std::vector<int>& target_word_int,
        const int num_results,
        const int counter_start,
        const int counter_stop)
    {
        for (int index = counter_start; index < counter_stop; ++index)
        {
            std::vector<int>& word = m_keys_encoded[index];
            double score = key_weighted_damerau_levenshtein(
                target_word_int,
                word,
                ((int)heap.size() < num_results) ? -1.0 : heap.top().score);

            if ((int)heap.size() < num_results)
            {
                heap.push({ index, score });
            }
            else if (score < heap.top().score)
            {
                heap.pop();
                heap.push({ index, score });
            }
        }
    };

    std::vector<std::tuple<std::vector<int>, double>> weighted_damerau_levenshtein(
        const std::vector<int>& target_word_int,
        int num_results)
    {
        num_results = std::max(num_results, 1);
        num_results = std::min(num_results, (int)(m_keys_encoded.size()));

        // max-heap of capacity num_results: top() is the worst (highest) accepted score
        // insertion is O(log[num_results])
        std::priority_queue<WordScore, std::vector<WordScore>> heap;

        populate_heap(
            heap,
            target_word_int,
            num_results,
            0,
            (int)m_keys_encoded.size());

        return sort_word_scores(heap);
    }

    std::vector<std::tuple<std::vector<int>, double>> weighted_damerau_levenshtein_multithread(
        const std::vector<int>& target_word_int,
        int num_results)
    {
        int thread_count = (int)std::thread::hardware_concurrency();
        num_results = std::max(num_results, 1);
        num_results = std::min(num_results, (int)(m_keys_encoded.size()));

        // each thread maintains its own heap to avoid synchronization overhead during scoring
        std::vector<std::priority_queue<WordScore, std::vector<WordScore>>> heaps(thread_count);
        int chunk_size = (int)std::ceil(m_keys_encoded.size() / (double)thread_count);
        int counter_start = 0;
        int counter_stop = 0;
        std::vector<std::thread> threads(thread_count);

        for (int i = 0; i < thread_count; ++i)
        {
            if (i == thread_count - 1)
            {
                // last thread takes any remaining items due to rounding
                counter_stop = (int)m_keys_encoded.size();
            }
            else
            {
                counter_stop = std::min(counter_start + chunk_size, (int)m_keys_encoded.size());
            }

            if (counter_start >= counter_stop)
            {
                break; // no more items to process, can happen if thread_count > m_keys_encoded.size()
            }

            threads[i] = std::thread(
                &WeightDamLeven::populate_heap,
                this,
                std::ref(heaps[i]),
                std::ref(target_word_int),
                num_results,
                counter_start,
                counter_stop);
            counter_start = counter_stop;
        }

        for (int i = 0; i < thread_count; ++i)
        {
            threads[i].join();
        }

        // merge thread-local heaps sequentially after all threads have finished
        std::priority_queue<WordScore, std::vector<WordScore>> merged_heap;
        for (auto& heap : heaps)
        {
            while (!heap.empty())
            {
                WordScore word_score = heap.top();
                heap.pop();
                if ((int)merged_heap.size() < num_results)
                {
                    merged_heap.push(word_score);
                }
                else if (word_score.score < merged_heap.top().score)
                {
                    merged_heap.pop();
                    merged_heap.push(word_score);
                }
            }
        }

        return sort_word_scores(merged_heap);
    }

    std::tuple<std::vector<int>, double> weighted_damerau_levenshtein_single(
        const std::vector<int>& target_word_int)
    {
        return weighted_damerau_levenshtein(target_word_int, 1)[0];
    }

    std::tuple<std::vector<int>, double> weighted_damerau_levenshtein_single_multithread(
        const std::vector<int>& target_word_int)
    {
        return weighted_damerau_levenshtein_multithread(target_word_int, 1)[0];
    }
};

PYBIND11_MODULE(weightdamleven, m)
{
    py::class_<WeightDamLeven>(m, "WeightDamLeven")
        .def(py::init<
                std::vector<std::vector<int>>&,
                std::vector<std::vector<double>>&,
                bool,
                double,
                double,
                double,
                double,
                double>(),
            "Constructor.",
            py::arg("keys_encoded"),
            py::arg("cost_matrix"),
            py::arg("is_key_cost"),
            py::arg("replace_cost"),
            py::arg("insert_cost"),
            py::arg("append_cost"),
            py::arg("delete_cost"),
            py::arg("transpose_cost"))
        .def("weighted_damerau_levenshtein",
            &WeightDamLeven::weighted_damerau_levenshtein,
            "Normal Search.",
            py::arg("target_word_int"),
            py::arg("num_results"))
        .def("weighted_damerau_levenshtein_multithread",
            &WeightDamLeven::weighted_damerau_levenshtein_multithread,
            "Multithreaded Search.",
            py::arg("target_word_int"),
            py::arg("num_results"))
        .def("weighted_damerau_levenshtein_single",
            &WeightDamLeven::weighted_damerau_levenshtein_single,
            "Find the single best match.",
            py::arg("target_word_int"))
        .def("weighted_damerau_levenshtein_single_multithread",
            &WeightDamLeven::weighted_damerau_levenshtein_single_multithread,
            "Multithreaded single best match.",
            py::arg("target_word_int"))
        .doc() = "WeightDamLeven is used to find close string matches.";
}
