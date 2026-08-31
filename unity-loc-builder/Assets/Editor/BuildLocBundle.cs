using UnityEngine;
using UnityEditor;
using System.IO;

public class BuildLocBundle
{
    [MenuItem("FF Tools/Build Localization Bundle")]
    public static void Build()
    {
        string assetPath = "Assets/BundleAssets/loc_pt-br.txt";
        
        AssetImporter importer = AssetImporter.GetAtPath(assetPath);
        if (importer == null)
        {
            Debug.LogError("Could not find asset at: " + assetPath);
            return;
        }
        importer.assetBundleName = "loc_pt-br";
        importer.SaveAndReimport();

        string outputPath = "Assets/StreamingAssets/BuiltBundles";
        if (!Directory.Exists(outputPath))
            Directory.CreateDirectory(outputPath);

        BuildPipeline.BuildAssetBundles(
            outputPath,
            BuildAssetBundleOptions.ChunkBasedCompression,
            BuildTarget.Android
        );

        string serverPath = Path.GetFullPath("../static/ABHotUpdates/android/optional/optionallocres/99/gameassetbundles");
        if (!Directory.Exists(serverPath))
            Directory.CreateDirectory(serverPath);

        string builtBundle = Path.Combine(outputPath, "loc_pt-br");
        if (File.Exists(builtBundle))
        {
            string destName = "loc_pt-br.LocalBundle2018~3D";
            string destPath = Path.Combine(serverPath, destName);
            File.Copy(builtBundle, destPath, true);
            Debug.Log("SUCCESS! Bundle copied to: " + destPath);
            Debug.Log("Bundle size: " + new FileInfo(destPath).Length + " bytes");
        }
        else
        {
            Debug.LogError("Build failed! Bundle not found at: " + builtBundle);
        }

        AssetDatabase.Refresh();
        Debug.Log("Build complete!");
    }
}
