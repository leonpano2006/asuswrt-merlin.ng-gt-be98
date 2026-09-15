/* SPDX-License-Identifier: GPL-2.0 */
/* Checked against all 12 task_struct DWARF definitions in Leon #32. */
#ifndef _GTBE98_CGROUP_ABI_H
#define _GTBE98_CGROUP_ABI_H

#ifdef CONFIG_GTBE98_MEMCG_ABI
#include <linux/slub_def.h>
#endif

#if defined(GTBE98) && defined(CONFIG_CGROUPS) && !defined(CONFIG_GTBE98_CGROUP_ABI)
#error "GT-BE98 cgroups require the checked core+pids ABI configuration"
#endif

#if defined(CONFIG_GTBE98_CGROUP_ABI) && defined(CONFIG_MEMCG) && !defined(CONFIG_GTBE98_MEMCG_ABI)
#error "GT-BE98 memory accounting requires its checked ABI configuration"
#endif
#if defined(CONFIG_GTBE98_MEMCG_ABI)
#if !defined(CONFIG_MEMCG) || !defined(CONFIG_GTBE98_CGROUP_ABI) || !defined(CONFIG_ARM64) || !defined(CONFIG_SLUB)
#error "GT-BE98 memcg ABI requires ARM64, SLUB, MEMCG and the core cgroup ABI"
#endif
#if defined(CONFIG_MEMCG_KMEM) || defined(CONFIG_NEED_MULTIPLE_NODES) || defined(CONFIG_GCC_PLUGIN_RANDSTRUCT)
#error "GT-BE98 memcg ABI excludes kernel slab charging, multiple nodes and random task layout"
#endif
#endif

static inline void gtbe98_cgroup_abi_check(void)
{
#ifdef CONFIG_GTBE98_CGROUP_ABI
	BUILD_BUG_ON(sizeof(struct task_struct) != 2688);
#ifdef CONFIG_GTBE98_MEMCG_ABI
	BUILD_BUG_ON(offsetof(struct task_struct, memcg_in_oom) != 2640);
	BUILD_BUG_ON(offsetof(struct task_struct, active_memcg) != 2664);
	BUILD_BUG_ON(sizeof(struct thread_struct) != 704);
	BUILD_BUG_ON(sizeof(struct mm_struct) != 848);
	BUILD_BUG_ON(offsetof(struct mm_struct, cpu_bitmap) != 848);
	BUILD_BUG_ON(sizeof(struct page) != 64);
	BUILD_BUG_ON(offsetof(struct page, mem_cgroup) != 56);
	BUILD_BUG_ON(sizeof(struct kmem_cache) != 240);
	BUILD_BUG_ON(offsetof(struct kmem_cache, random) != 208);
	BUILD_BUG_ON(offsetof(struct kmem_cache, node) != 232);
	BUILD_BUG_ON(sizeof(struct lruvec) != 128);
	BUILD_BUG_ON(sizeof(struct pglist_data) != 5312);
	BUILD_BUG_ON(offsetof(struct pglist_data, flags) != 5024);
#endif

	BUILD_BUG_ON(__alignof__(struct task_struct) != 64);
	BUILD_BUG_ON(sizeof(struct sched_entity) != 192);
	BUILD_BUG_ON(offsetof(struct task_struct, cgroups) != 144);
	BUILD_BUG_ON(offsetof(struct task_struct, cg_list) != 152);
#ifdef CONFIG_SECCOMP
	BUILD_BUG_ON(offsetof(struct task_struct, seccomp) != 168);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->seccomp) != 16);
#else
	BUILD_BUG_ON(offsetof(struct task_struct, seccomp) != 1600);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->seccomp) != 0);
#endif
	BUILD_BUG_ON(offsetof(struct task_struct, thread_info) != 0);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->thread_info) != 32);
	BUILD_BUG_ON(offsetof(struct task_struct, state) != 32);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->state) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, stack) != 40);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->stack) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, usage) != 48);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->usage) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, flags) != 52);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->flags) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, ptrace) != 56);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->ptrace) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, wake_entry) != 64);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->wake_entry) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, on_cpu) != 72);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->on_cpu) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, cpu) != 76);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->cpu) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, wakee_flips) != 80);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->wakee_flips) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, wakee_flip_decay_ts) != 88);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->wakee_flip_decay_ts) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, last_wakee) != 96);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->last_wakee) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, recent_used_cpu) != 104);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->recent_used_cpu) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, wake_cpu) != 108);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->wake_cpu) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, on_rq) != 112);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->on_rq) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, prio) != 116);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->prio) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, static_prio) != 120);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->static_prio) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, normal_prio) != 124);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->normal_prio) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, rt_priority) != 128);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->rt_priority) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, sched_class) != 136);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->sched_class) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, se) != 192);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->se) != 192);
	BUILD_BUG_ON(offsetof(struct task_struct, rt) != 384);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->rt) != 48);
	BUILD_BUG_ON(offsetof(struct task_struct, dl) != 432);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->dl) != 224);
	BUILD_BUG_ON(offsetof(struct task_struct, policy) != 656);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->policy) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, nr_cpus_allowed) != 660);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->nr_cpus_allowed) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, cpus_allowed) != 664);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->cpus_allowed) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, cpus_hint) != 672);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->cpus_hint) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, rcu_read_lock_nesting) != 680);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->rcu_read_lock_nesting) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, rcu_read_unlock_special) != 684);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->rcu_read_unlock_special) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, rcu_node_entry) != 688);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->rcu_node_entry) != 16);
	BUILD_BUG_ON(offsetof(struct task_struct, rcu_blocked_node) != 704);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->rcu_blocked_node) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, rcu_tasks_nvcsw) != 712);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->rcu_tasks_nvcsw) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, rcu_tasks_holdout) != 720);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->rcu_tasks_holdout) != 1);
	BUILD_BUG_ON(offsetof(struct task_struct, rcu_tasks_idx) != 721);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->rcu_tasks_idx) != 1);
	BUILD_BUG_ON(offsetof(struct task_struct, rcu_tasks_idle_cpu) != 724);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->rcu_tasks_idle_cpu) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, rcu_tasks_holdout_list) != 728);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->rcu_tasks_holdout_list) != 16);
	BUILD_BUG_ON(offsetof(struct task_struct, sched_info) != 744);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->sched_info) != 0);
	BUILD_BUG_ON(offsetof(struct task_struct, tasks) != 744);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->tasks) != 16);
	BUILD_BUG_ON(offsetof(struct task_struct, pushable_tasks) != 760);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->pushable_tasks) != 40);
	BUILD_BUG_ON(offsetof(struct task_struct, pushable_dl_tasks) != 800);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->pushable_dl_tasks) != 24);
	BUILD_BUG_ON(offsetof(struct task_struct, mm) != 824);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->mm) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, active_mm) != 832);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->active_mm) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, vmacache) != 840);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->vmacache) != 40);
	BUILD_BUG_ON(offsetof(struct task_struct, rss_stat) != 880);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->rss_stat) != 20);
	BUILD_BUG_ON(offsetof(struct task_struct, exit_state) != 900);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->exit_state) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, exit_code) != 904);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->exit_code) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, exit_signal) != 908);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->exit_signal) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, pdeath_signal) != 912);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->pdeath_signal) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, jobctl) != 920);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->jobctl) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, personality) != 928);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->personality) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, atomic_flags) != 944);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->atomic_flags) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, restart_block) != 952);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->restart_block) != 48);
	BUILD_BUG_ON(offsetof(struct task_struct, pid) != 1000);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->pid) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, tgid) != 1004);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->tgid) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, stack_canary) != 1008);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->stack_canary) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, real_parent) != 1016);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->real_parent) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, parent) != 1024);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->parent) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, children) != 1032);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->children) != 16);
	BUILD_BUG_ON(offsetof(struct task_struct, sibling) != 1048);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->sibling) != 16);
	BUILD_BUG_ON(offsetof(struct task_struct, group_leader) != 1064);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->group_leader) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, ptraced) != 1072);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->ptraced) != 16);
	BUILD_BUG_ON(offsetof(struct task_struct, ptrace_entry) != 1088);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->ptrace_entry) != 16);
	BUILD_BUG_ON(offsetof(struct task_struct, thread_pid) != 1104);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->thread_pid) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, pid_links) != 1112);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->pid_links) != 64);
	BUILD_BUG_ON(offsetof(struct task_struct, thread_group) != 1176);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->thread_group) != 16);
	BUILD_BUG_ON(offsetof(struct task_struct, thread_node) != 1192);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->thread_node) != 16);
	BUILD_BUG_ON(offsetof(struct task_struct, vfork_done) != 1208);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->vfork_done) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, set_child_tid) != 1216);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->set_child_tid) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, clear_child_tid) != 1224);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->clear_child_tid) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, utime) != 1232);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->utime) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, stime) != 1240);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->stime) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, gtime) != 1248);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->gtime) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, prev_cputime) != 1256);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->prev_cputime) != 24);
	BUILD_BUG_ON(offsetof(struct task_struct, nvcsw) != 1280);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->nvcsw) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, nivcsw) != 1288);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->nivcsw) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, start_time) != 1296);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->start_time) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, real_start_time) != 1304);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->real_start_time) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, min_flt) != 1312);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->min_flt) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, maj_flt) != 1320);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->maj_flt) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, cputime_expires) != 1328);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->cputime_expires) != 24);
	BUILD_BUG_ON(offsetof(struct task_struct, cpu_timers) != 1352);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->cpu_timers) != 48);
	BUILD_BUG_ON(offsetof(struct task_struct, ptracer_cred) != 1400);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->ptracer_cred) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, real_cred) != 1408);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->real_cred) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, cred) != 1416);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->cred) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, comm) != 1424);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->comm) != 16);
	BUILD_BUG_ON(offsetof(struct task_struct, nameidata) != 1440);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->nameidata) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, sysvsem) != 1448);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->sysvsem) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, sysvshm) != 1456);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->sysvshm) != 16);
	BUILD_BUG_ON(offsetof(struct task_struct, fs) != 1472);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->fs) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, files) != 1480);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->files) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, nsproxy) != 1488);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->nsproxy) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, signal) != 1496);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->signal) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, sighand) != 1504);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->sighand) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, blocked) != 1512);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->blocked) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, real_blocked) != 1520);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->real_blocked) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, saved_sigmask) != 1528);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->saved_sigmask) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, pending) != 1536);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->pending) != 24);
	BUILD_BUG_ON(offsetof(struct task_struct, sas_ss_sp) != 1560);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->sas_ss_sp) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, sas_ss_size) != 1568);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->sas_ss_size) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, sas_ss_flags) != 1576);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->sas_ss_flags) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, task_works) != 1584);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->task_works) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, audit_context) != 1592);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->audit_context) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, parent_exec_id) != 1600);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->parent_exec_id) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, self_exec_id) != 1608);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->self_exec_id) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, alloc_lock) != 1616);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->alloc_lock) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, pi_lock) != 1620);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->pi_lock) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, wake_q) != 1624);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->wake_q) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, pi_waiters) != 1632);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->pi_waiters) != 16);
	BUILD_BUG_ON(offsetof(struct task_struct, pi_top_task) != 1648);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->pi_top_task) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, pi_blocked_on) != 1656);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->pi_blocked_on) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, journal_info) != 1664);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->journal_info) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, bio_list) != 1672);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->bio_list) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, plug) != 1680);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->plug) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, reclaim_state) != 1688);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->reclaim_state) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, backing_dev_info) != 1696);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->backing_dev_info) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, io_context) != 1704);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->io_context) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, ptrace_message) != 1712);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->ptrace_message) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, last_siginfo) != 1720);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->last_siginfo) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, ioac) != 1728);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->ioac) != 0);
	BUILD_BUG_ON(offsetof(struct task_struct, robust_list) != 1728);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->robust_list) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, compat_robust_list) != 1736);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->compat_robust_list) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, pi_state_list) != 1744);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->pi_state_list) != 16);
	BUILD_BUG_ON(offsetof(struct task_struct, pi_state_cache) != 1760);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->pi_state_cache) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, futex_exit_mutex) != 1768);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->futex_exit_mutex) != 32);
	BUILD_BUG_ON(offsetof(struct task_struct, futex_state) != 1800);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->futex_state) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, rseq) != 1808);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->rseq) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, rseq_len) != 1816);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->rseq_len) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, rseq_sig) != 1820);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->rseq_sig) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, rseq_event_mask) != 1824);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->rseq_event_mask) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, tlb_ubc) != 1832);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->tlb_ubc) != 0);
	BUILD_BUG_ON(offsetof(struct task_struct, rcu) != 1832);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->rcu) != 16);
	BUILD_BUG_ON(offsetof(struct task_struct, splice_pipe) != 1848);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->splice_pipe) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, task_frag) != 1856);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->task_frag) != 16);
	BUILD_BUG_ON(offsetof(struct task_struct, nr_dirtied) != 1872);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->nr_dirtied) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, nr_dirtied_pause) != 1876);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->nr_dirtied_pause) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, dirty_paused_when) != 1880);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->dirty_paused_when) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, timer_slack_ns) != 1888);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->timer_slack_ns) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, default_timer_slack_ns) != 1896);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->default_timer_slack_ns) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, pagefault_disabled) != 1904);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->pagefault_disabled) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, psi_flags) != 1908);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->psi_flags) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, oom_reaper_list) != 1912);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->oom_reaper_list) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, stack_vm_area) != 1920);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->stack_vm_area) != 8);
	BUILD_BUG_ON(offsetof(struct task_struct, stack_refcount) != 1928);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->stack_refcount) != 4);
	BUILD_BUG_ON(offsetof(struct task_struct, thread) != 1936);
	BUILD_BUG_ON(sizeof(((struct task_struct *)0)->thread) != 704);
#endif
}

#endif
