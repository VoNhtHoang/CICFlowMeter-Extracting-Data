package cic.cs.unb.ca.ifm;

import cic.cs.unb.ca.flow.FlowMgr;
import cic.cs.unb.ca.jnetpcap.BasicFlow;
import cic.cs.unb.ca.jnetpcap.FlowFeature;
import cic.cs.unb.ca.jnetpcap.worker.InsertCsvRow;
import cic.cs.unb.ca.jnetpcap.worker.CmdRealTimeFlowWorker;
import cic.cs.unb.ca.jnetpcap.worker.FlowZmqPublisher;

import org.apache.commons.lang3.StringUtils;
import org.jnetpcap.Pcap;
import org.jnetpcap.PcapIf;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.HashMap;
import java.util.Map;


// ===== SUPPORT LIBS ======
import org.json.simple.JSONObject;


public class RT_cmd {

    public static final Logger logger = LoggerFactory.getLogger(RT_cmd.class);

    private static List<PcapIf> pcapIfs = new ArrayList<>();
    private static CmdRealTimeFlowWorker worker;
    private static Thread workerThread;

    private static ExecutorService csvWriterThread;
    // private static FlowZmqPublisher publishZmq = new FlowZmqPublisher();
    private static String pcapIfName;
    private static String outputDir;

    private static long flowTimeout = 360000L;
    private static long activityTimeout = 120_000_000L;

    private static volatile boolean running = true;

    public static void main(String[] args) throws Exception {

        if (args.length < 1) {
            helper();
            return;
        }

        parseArgs(args);

        FlowMgr.getInstance().init();
        csvWriterThread = Executors.newSingleThreadExecutor();

        startRealtimeFlow();
        startKeyListener();

        // block main thread
        while (running) {
            Thread.sleep(500);
        }

        shutdown();
        System.out.println("[INFO] RT_cmd exited cleanly");
        System.exit(0);
    }

    /* ======================= CORE ======================= */

    private static void startRealtimeFlow() {

        worker = new CmdRealTimeFlowWorker(
                pcapIfName,
                flowTimeout,
                activityTimeout
        );

        workerThread = new Thread(worker, "pcap-worker");
        workerThread.start();

        logger.info("Realtime traffic flow started");
    }

    public static void insertRtFlow(BasicFlow flow) {

        List<String> flowStringList = new ArrayList<>();
        // List<String[]> flowDataList = new ArrayList<>();
        String flowDump = flow.dumpFlowBasedFeaturesEx();
        System.out.println(flowDump);
        // flowStringList.add(flowDump);
        // flowDataList.add(StringUtils.split(flowDump, ","));

        //write flows to csv file
        String header  = FlowFeature.getHeader();
        String path = FlowMgr.getInstance().getSavePath();
        String filename = LocalDate.now().toString() + FlowMgr.FLOW_SUFFIX;
        // csvWriterThread.execute(new InsertCsvRow(header, flowStringList, path, filename));
        
        csvWriterThread.execute(() -> 
        {
            sendFlow(header, flowDump);
        });

    }

    private static void sendFlow(String header, String flowDump){
        // JSONObject data = new JSONObject();
        Map<String, String> data = new HashMap<String, String>();

        data.put("header", header);
        data.put("flowDump", flowDump);

        JSONObject obj = new JSONObject(data);

        FlowZmqPublisher.send(obj.toJSONString().getBytes(java.nio.charset.StandardCharsets.UTF_8), 0);
    }

    private static void stopRealtimeFlow() {

        running = false;

        if (worker != null) {
            worker.stop();
        }

        if (workerThread != null) {
            workerThread.interrupt();
        }
    }

    private static void shutdown() {

        logger.info("Shutting down CSV writer...");

        try {
            csvWriterThread.awaitTermination(10, TimeUnit.SECONDS);
            } catch (InterruptedException e) {
                csvWriterThread.shutdownNow();
            }

        FlowZmqPublisher.close();    
        // String path = FlowMgr.getInstance().getAutoSaveFile();

        // if (path != null && new File(path).exists()) {
        //     System.out.println("[INFO] CSV saved at: " + path);
        // }
    }

    /* ======================= CLI ======================= */

    private static void startKeyListener() {

        Thread keyThread = new Thread(() -> {
            try {
                System.out.println("[INFO] Press 'q' then ENTER to stop...");
                while (true) {
                    int c = System.in.read();
                    if (c == 'q' || c == 'Q') {
                        System.out.println("[INFO] Stop signal received");
                        stopRealtimeFlow();
                        break;
                    }
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        });

        keyThread.setDaemon(true);
        keyThread.start();
    }

    private static void parseArgs(String[] args) throws Exception {

        for (int i = 0; i < args.length; i++) {

            switch (args[i]) {

                case "-h":
                case "--help":
                    helper();
                    System.exit(0);
                    break;

                case "-l":
                case "--list-interface":
                    listPcapIfs();
                    System.exit(0);
                    break;

                case "-i":
                case "--interface":
                    pcapIfName = args[++i];
                    break;

                case "-o":
                    outputDir = args[++i];
                    break;

                case "-fto":
                case "--flowTimeout":
                    flowTimeout = Long.parseLong(args[++i]);
                    break;

                case "-ato":
                case "--activityTimeout":
                    activityTimeout = Long.parseLong(args[++i]);
                    break;
            }
        }
    }

    private static void listPcapIfs() {

        StringBuilder errbuf = new StringBuilder();
        if (Pcap.findAllDevs(pcapIfs, errbuf) != Pcap.OK) {
            throw new RuntimeException(errbuf.toString());
        }

        System.out.println("[DEBUG ]Available "+ pcapIfs.size() +" interfaces:");
        for (PcapIf p : pcapIfs) {
            System.out.println(" - " + p.getName() + " : " + p.getDescription());
        }
    }

    private static void helper() {
        System.out.println("CICFlowMeter RT_cmd usage:");
        System.out.println(" -i <interface>");
        System.out.println(" -fto <flow timeout>");
        System.out.println(" -ato <activity timeout>");
        System.out.println(" -o <output dir>");
        System.out.println(" -l --list-interface");
    }
}
