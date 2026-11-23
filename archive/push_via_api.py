()]
    message = git(repo_dir, "log", "-1", "--format=%B", commit_sha)
    author_name = git(repo_dir, "log", "-1", "--format=%an", commit_sha)
    author_email = git(repo_dir, "log", "-1", "--format=%ae", commit_sha)
    author_date = git(repo_dir, "log", "-1", "--format=%aI", commit_sha)

    print(f"commit {commit_sha[:10]} parent {parent[:10]} files={files}")

    tree_entries = []
    for path in files:
        content = git_raw(repo_dir, "show", f"{commit_sha}:{path}")
        blob = api(
            "POST",
            f"/repos/{repo}/git/blobs",
            token,
            {
                "content": base64.b64encode(content.encode()).decode(),
                "encoding": "base64",
            },
        )
        mode = "100755" if git(repo_dir, "ls-files", "-s", "--", path).split()[0] == "100755" else "100644"
        tree_entries.append({"path": path, "mode": mode, "type": "blob", "sha": blob["sha"]})
        print(f"  blob {path} -> {blob['sha'][:10]}")

    base_tree = api("GET", f"/repos/{repo}/git/commits/{parent}", token)["tree"]["sha"]
    tree = api(
        "POST",
        f"/repos/{repo}/git/trees",
        token,
        {"base_tree": base_tree, "tree": tree_entries},
    )
    print(f"  tree -> {tree['sha'][:10]}")

    new_commit = api(
        "POST",
        f"/repos/{repo}/git/commits",
        token,
        {
            "message": message,
            "tree": tree["sha"],
            "parents": [parent],
            "author": {"name": author_name, "email": author_email, "date": author_date},
            "committer": {"name": author_name, "email": author_email, "date": author_date},
        },
    )
    print(f"  commit -> {new_commit['sha'][:10]}")

    ref_path = f"refs/heads/{branch}"
    try:
        api(
            "PATCH",
            f"/repos/{repo}/git/{ref_path}",
            token,
            {"sha": new_commit["sha"], "force": True},
        )
        print(f"  updated existing ref {branch}")
    except SystemExit:
        api(
            "POST",
            f"/repos/{repo}/git/refs",
            token,
            {"ref": ref_path, "sha": new_commit["sha"]},
        )
        print(f"  created new ref {branch}")

    print("pushed successfully via API")


if __name__ == "__main__":
    main()