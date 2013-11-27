from MySQLdb import connect
from argparse import ArgumentParser
import wimport_lib
from config import logger
from config import OUTPUT_PARTICIPANTS, OUTPUT_WEBINARS, DETAILS_MARK
from config import DB_NAME, SERVER_NAME, USER, PASS, W_TABLE, P_TABLE 
from config import LOG_FILE, LOG_FILE_PATH



# display log location in case of premature program exit 
print '''
Writing log to file "{}"
at path "{}"
'''.format(LOG_FILE, LOG_FILE_PATH)

# parse CLI options
parser = ArgumentParser(description='''Gather participants and webinars 
info from multiple files of attendees for GotoWebinar webinars''')
parser.add_argument('-i', '--input_dir', 
                    help='Directory containing input csv files', 
                    required=True)
parser.add_argument('-d', '--write_to_db', 
                    help='Write info to database also', 
                    action="store_true")
args = parser.parse_args()

# cycle through files in input dir and gather info in dictionaries
#    containing lists of lists
w_dict, p_dict = {}, {}
p_headers_list = []
p_no_sum = 0
for input_file in wimport_lib.find_csv_filenames(args.input_dir):
    # get webinar and participants info
    w_info = wimport_lib.get_webinar_info(input_file, DETAILS_MARK)
    w_id = wimport_lib.get_parameter('Webinar ID', w_info[0], w_info[1])
    p_info = wimport_lib.get_participants_info(input_file, w_id, DETAILS_MARK)
    p_len = len(p_info[1])
    p_no_sum += p_len
    logger.info("Reading {} \n\t --> {} participants.".format(input_file, p_len))
    # store info for later writing to files and database
    if w_id not in w_dict:
        w_dict[w_id] = [w_info[1]]
    else:
        w_dict[w_id] += [w_info[1]]
    if w_id not in p_dict:
        p_dict[w_id] = p_info[1]
    else:
        p_dict[w_id] += p_info[1]
    p_headers_list += [p_info[0]]	

# get headers and values for webinars
w_header = w_info[0]
w_values = []
for key in w_dict:
    w_values += w_dict[key]

logger.info("Processing gathered information...")    
# get headers and values for participants
p_header, p_values, diffs = p_headers_list[0], [], []
for h in p_headers_list[1:]:
    # try to find differences in participants headers 
    if len(p_header) < len(h):
        diffs = [x for x in h if x not in p_header]
        p_header = h
        break
    elif len(h) < len(p_header):
        diffs = [x for x in p_header if x not in h]
        break

if diffs:
    diffs_pos = [p_header.index(x) for x in diffs]

for key in p_dict:
    for row in p_dict[key]: 
        if len(row) < len(p_header):
            # handle differences in input files headers
            if not diffs:
                logger.error("Header longer than row but no diffs were detected.")
                exit(1)
            for pos in diffs_pos:
                insert_pos = int(pos)
                row.insert(insert_pos, "")
        elif len(row) > len(p_header):
            logger.error('''Participants row longer than header:
webinar id:{}
final_participants_header:{}
row:{}
'''.format(key, p_header, row))
            exit(1)
        else:
            break
    p_values += p_dict[key]

p_final_no = len(p_values)
w_final_no = len(w_values)
logger.info("Total: {} participants, {} webinars.".format(p_final_no, w_final_no))
# write output files
logger.info("Writing output files:")
wimport_lib.write_to_csv(OUTPUT_WEBINARS, w_header, w_values)
wimport_lib.write_to_csv(OUTPUT_PARTICIPANTS, p_header, p_values)

# write to database
if args.write_to_db:
    logger.info("Writing do database:")
    conn = connect(SERVER_NAME, USER, PASS, DB_NAME)
    with conn:
        cur = conn.cursor()
        wimport_lib.write_sql_table(cur, DB_NAME, W_TABLE, 
                                    w_header, w_values)
        wimport_lib.write_sql_table(cur, DB_NAME, P_TABLE, 
                                    p_header, p_values)

# log errors if any
if p_no_sum != p_final_no:
    logger.error('''Total participants number after processing differs from 
initial value.Some lines might have been lost in processing.''')


