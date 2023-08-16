import argparse
import sys
import time
import urllib.parse

import requests


KEYS = ['html_url', 'title', 'state', 'created_at', 'closed_at']
ALL_KEYS = KEYS + ['assignee', 'labels']


def extract_issue_information(pr):
    pr_info = []
    for key in KEYS:
        if key == 'title':
            # Make it CSV friendly
            pr_info.append(pr[key].replace(',', '/'))
        else:
            pr_info.append(pr[key])

    if pr['assignee']:
        pr_info.append(pr['assignee']['login'])
    elif pr['user']:
        pr_info.append(pr['user']['login'])
    else:
        pr_info.append('')

    # extract labels
    if pr['labels']:
        pr_info.append(' '.join(label['name'] for label in pr['labels']))
    else:
        pr_info.append('')

    return pr['number'], pr_info


def get_prs(args):
    api_url_template = 'https://api.github.com/search/issues?sort=created&order=desc&per_page={}&page={}&q=repo:{}/{}+{}'

    all_prs = {}
    page = 1
    while True:
        next_page_api_url = api_url_template.format(
            args.page_size,
            page,
            urllib.parse.quote(args.owner),
            urllib.parse.quote(args.repo),
            urllib.parse.quote(args.query, safe='+')
        )

        print(f'Geting git issue : {next_page_api_url}')
        response = requests.get(next_page_api_url)

        if response.status_code not in (200, 201):
            print(f'Failed to get PRs for {next_page_api_url}, error_code={response.status_code}, reason={response.reason}')
            break

        prs = response.json()
        if not prs or not prs['total_count']:
            print('Finished getting all git issues')
            break

        for pr in prs["items"]:
            pr_url, pr_info = extract_issue_information(pr)
            assert pr_url not in all_prs
            all_prs[pr_url] = pr_info

        if prs['incomplete_results']:
            print('Got imcomplete results for {}, expected={}, got={}'.format(
                next_page_api_url, args.page_size, prs['total_count']))
        elif len(prs['items']) < args.page_size:
            print('Finished getting all git issues')
            break

        print('Got total={} git issues so far'.format(len(all_prs)))

        page += 1

        time.sleep(10)

    return all_prs


def write_prs_to_file(prs, filename):
    if not prs:
        return

    print('Write total={} git issues to csv file'.format(len(prs)))

    if filename:
        f = open(filename, 'a+')
    else:
        f = sys.stdout

    # Write header
    f.write("{}\n".format(','.join(ALL_KEYS)))

    # Write all pull requests
    for _, pr in prs.items():
        f.write("{}\n".format(','.join(pr)))

    f.close()


def main():
    parser = argparse.ArgumentParser(
        prog='git_issues', description='get github issues')

    parser.add_argument('-f', '--file', default='git_issues.csv',
                        help="Write git issues to the target file")
    parser.add_argument('-o', '--owner', required=True)
    parser.add_argument('-r', '--repo', required=True)
    parser.add_argument('-q', '--query', default='is:pr+is:merged',
                        help='is:pr+is:merged+state:closed+-label:pr-backport+-label:pr-cherrypick+-label:pr-documentation+closed:>=2021-02-01 or ...closed:2021-02-01..2021-04-01')
    parser.add_argument('-p', '--page_size', type=int, default=100)
    args = parser.parse_args()

    write_prs_to_file(get_prs(args), args.file)


if __name__ == '__main__':
    main()
